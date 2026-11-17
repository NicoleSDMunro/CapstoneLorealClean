"""Busca de planos de abastecimento condicionada às premissas do Smart Launch.

Esta é uma busca em uma grade finita (2,5 p.p. por lote) com amostragem
reprodutível quando a grade excede o orçamento. NÃO é uma otimização global
certificada, nem ordem de produção. Os candidatos usam a MESMA sacola de
demanda e são verificados no motor principal antes de serem apresentados.
"""
from itertools import product as cartesian_product

import numpy as np
import pandas as pd

from smartlaunch_core import LIM, AUMENTO_MAX_RUPTURA, label
from smartlaunch_impact import (
    editable_lots, simulate_monthly_scenario, month_signals, tcc_check,
)


def _candidate_grid(lots, max_pct, max_increase_pct, budget, seed):
    """Percentuais positivos = cortes; negativos = aumentos de produção."""
    step = 2.5
    cut_levels = np.arange(0, max_pct + 0.001, step)
    increase_levels = np.arange(-max_increase_pct, -0.001, 5.0)
    levels = np.round(np.concatenate((increase_levels, cut_levels)), 2)
    zero_index = int(np.flatnonzero(levels == 0)[0])
    dimension = len(lots)
    space_size = len(levels) ** dimension
    if space_size <= budget:
        cuts = np.asarray(list(cartesian_product(levels, repeat=dimension)),
                          dtype=float)
    else:
        rng = np.random.default_rng(seed)
        seen = set()
        selections = []

        def add(index_tuple):
            key = tuple(int(i) for i in index_tuple)
            if key not in seen:
                seen.add(key)
                selections.append(key)

        add([zero_index] * dimension)
        for j in range(dimension):
            for i in range(len(levels)):
                if i == zero_index:
                    continue
                vector = [zero_index] * dimension
                vector[j] = i
                add(vector)
        for i in range(len(levels)):
            if i != zero_index:
                add([i] * dimension)
        for j in range(dimension):
            for k in range(j + 1, dimension):
                for i in range(len(levels)):
                    if i == zero_index:
                        continue
                    v = [zero_index] * dimension
                    v[j] = i
                    v[k] = i
                    add(v)
        # Âncoras com remanejamento (aumento em um lote e corte no outro).
        inc_index = zero_index - 1 if zero_index > 0 else None
        cut_index = min(len(levels) - 1, zero_index + 4)
        if inc_index is not None:
            for j in range(dimension):
                for k in range(dimension):
                    if j == k:
                        continue
                    v = [zero_index] * dimension
                    v[j] = inc_index
                    v[k] = cut_index
                    add(v)

        # Amostrar aumentos e cortes, enfatizando movimentos pequenos
        # perto de zero, com algumas combinações de maior impacto.
        tries = 0
        while len(selections) < budget and tries < budget * 30:
            tries += 1
            if tries % 3 == 0:
                v = rng.integers(0, len(levels), size=dimension)
            else:
                weights = 1.0 / (1.0 + np.abs(levels) / 7.5)
                v = rng.choice(len(levels), size=dimension,
                               p=weights / weights.sum())
            add(v)
        cuts = levels[np.asarray(selections[:budget], dtype=int)]
    return cuts, int(space_size)


def _future_required(demand, days):
    """Demanda necessária nos dias de cobertura, com cauda extrapolada."""
    n, months = demand.shape
    q = float(days) / 30.0
    whole = int(q)
    fraction = q - whole
    required = np.zeros((n, months), dtype=float)
    for j in range(months):
        for offset in range(1, whole + 1):
            required[:, j] += demand[:, min(j + offset, months - 1)]
        if fraction:
            required[:, j] += fraction * demand[
                :, min(j + whole + 1, months - 1)
            ]
    return required


def search_supply_combinations(
    res, close, *, budget=5000, max_cut_pct=50,
    max_increase_pct=10,
    coverage_days=180, uncertainty_multiplier=1.0,
    fill_drop_limit_pp=0.2, rupture_rise_limit_pp=2.5,
    seed=20261021, top_k=12
):
    """Busca cortes e aumentos combinados nos lotes teoricamente negociáveis.

    Critério de ordenação: menor *maior excedente médio mensal* na janela
    crítica avaliável; desempates por menor aumento de vendas perdidas e
    menor corte total. Conserva fill rate, não cria novo alerta de ruptura
    e respeita o aumento mensal exploratório máximo de ruptura.

    Com grade maior que orçamento, avalia uma AMOSTRA reproduzível e
    não declara ótimo global. A triagem vetorizada é revalidada com
    simulate_monthly_scenario e tcc_check (nas premissas padrão).
    """
    if int(budget) not in (1000, 2500, 5000, 10000):
        raise ValueError("Orçamento deve ser 1.000, 2.500, 5.000 ou 10.000.")
    if max_cut_pct < 2.5 or max_cut_pct > 75 or max_cut_pct % 2.5:
        raise ValueError("Corte máximo deve ser múltiplo de 2,5% até 75%.")
    if max_increase_pct not in (0, 5, 10, 15, 20):
        raise ValueError("Aumento máximo deve ser 0%, 5%, 10%, 15% ou 20%.")
    if not 0 <= fill_drop_limit_pp <= 5:
        raise ValueError("Queda máxima de fill rate inválida.")
    if not 0 <= rupture_rise_limit_pp <= 20:
        raise ValueError("Aumento máximo de ruptura inválido.")
    if not 30 <= float(coverage_days) <= 360:
        raise ValueError("Cobertura deve estar entre 30 e 360 dias.")
    if not 0.5 <= float(uncertainty_multiplier) <= 2:
        raise ValueError("Multiplicador de incerteza inválido.")

    original = np.asarray(res["production"], dtype=float)
    dm0 = np.asarray(res["dm"], dtype=float)
    center = np.asarray(res["center"], dtype=float)
    months = res["months"]
    n, h = dm0.shape
    active = np.asarray(res["active"], dtype=bool)
    evaluated = np.asarray(
        res.get("evaluated", [j < h - 1 for j in range(h)]), dtype=bool
    )
    scored_months = np.flatnonzero(active & evaluated)
    if not len(scored_months):
        raise ValueError("Não há mês de excesso avaliável na janela crítica.")
    eligible = [
        item for item in editable_lots(res, close)
        if item["index"] <= scored_months[-1]
        and original[item["index"]] > 0
    ]
    if not eligible:
        return dict(
            candidates_checked=0, grid_size=0, eligible_lots=[],
            shortlist=pd.DataFrame(), plans={}, n_admissible_screened=0,
            best=None, reason="Nenhum lote positivo elegível influencia os meses "
                              "de excesso avaliados na janela crítica."
        )

    indices = np.asarray([x["index"] for x in eligible], dtype=int)
    cuts, space = _candidate_grid(eligible, max_cut_pct, max_increase_pct,
                                  int(budget), int(seed))
    k = len(cuts)
    plan_candidates = np.tile(original, (k, 1))
    plan_candidates[:, indices] = (
        original[indices][None, :] *
        (1.0 - cuts / 100.0)
    )
    # No modelo operacional, quantidades podem ter casas decimais no plano
    # original. Preservar exatamente o valor original quando o corte é zero.
    # Volumes de cortes E aumentos são arredondados para unidades.
    changed = cuts != 0
    plan_candidates[:, indices] = np.where(
        changed, np.rint(plan_candidates[:, indices]),
        original[indices][None, :]
    )
    demand = (
        dm0 if abs(uncertainty_multiplier - 1.0) < 1e-12 else
        np.maximum(0, center[None, :] +
                   uncertainty_multiplier * (dm0 - center[None, :]))
    )
    required = _future_required(demand, coverage_days)

    def batch_metrics(plans):
        batch = len(plans)
        available = np.full((batch, n), float(res["e0"]), dtype=float)
        lost_total = np.zeros(batch)
        ru_prob = np.zeros((batch, h))
        excess_prob = np.full((batch, h), np.nan)
        excess_mean = np.full((batch, h), np.nan)
        for j in range(h):
            supply = np.maximum(0, available + plans[:, j, None])
            lost = np.maximum(0, demand[None, :, j] - supply)
            available = np.maximum(0, supply - demand[None, :, j])
            if active[j]:
                lost_total += lost.sum(axis=1)
            ru_prob[:, j] = (lost > 0).mean(axis=1) * 100
            if evaluated[j]:
                excess_prob[:, j] = (
                    (available > 0) &
                    (available >= required[None, :, j])
                ).mean(axis=1) * 100
                if active[j]:
                    excess_mean[:, j] = np.maximum(
                        0, available - required[None, :, j]
                    ).mean(axis=1)
        return ru_prob, excess_prob, excess_mean, lost_total / n

    base_ru, base_ex, base_vol, base_lost = batch_metrics(original[None, :])
    base_ru, base_ex = base_ru[0], base_ex[0]
    base_peak = float(np.nanmax(base_vol[0, scored_months]))
    demand_total = float(demand[:, active].sum())
    base_fill = 100 * (1 - float(base_lost[0]) * n / demand_total) \
                if demand_total > 0 else 100.0

    screening = []
    block = 64
    for start in range(0, k, block):
        end = min(k, start + block)
        ru, ex, vol, lost = batch_metrics(plan_candidates[start:end])
        fill = 100 * (1 - lost * n / demand_total) if demand_total else \
               np.full(len(lost), 100.0)
        rise = np.max(ru[:, active] - base_ru[None, active], axis=1)
        new_ru = np.any(
            (ru[:, active] > 2.5) & (base_ru[None, active] <= 2.5),
            axis=1
        )
        new_ex = np.any(
            (ex[:, scored_months] > 2.5) &
            (base_ex[None, scored_months] <= 2.5),
            axis=1
        )
        peak = np.nanmax(vol[:, scored_months], axis=1)
        feasible = (
            (fill >= base_fill - fill_drop_limit_pp - 1e-8) &
            (rise <= rupture_rise_limit_pp + 1e-8) &
            (~new_ru) & (~new_ex)
        )
        for i in range(end - start):
            global_i = start + i
            if feasible[i] and peak[i] < base_peak - 1e-7:
                screening.append((
                    float(peak[i]),
                    float(lost[i] - base_lost[0]),
                    float(np.sum(np.abs(original - plan_candidates[global_i]))),
                    global_i
                ))
    screening.sort()
    # Revalidar os melhores candidatos pela função exata já usada no site.
    # Verificar até 100 propostas melhora o resultado se alguma for eliminada
    # durante a conferência com percentis do protocolo original do TCC.
    selected = []
    plans = {}
    base_signals = None
    standard_assumptions = (
        int(coverage_days) == int(LIM) and
        abs(float(uncertainty_multiplier) - 1) < 1e-12
    )
    if standard_assumptions:
        base_signals = month_signals(res, original)
    for _, _, _, i in screening[:100]:
        plan = plan_candidates[i].copy()
        detail = simulate_monthly_scenario(
            res, plan, coverage_days=coverage_days,
            uncertainty_multiplier=uncertainty_multiplier
        )
        diff = detail["delta"]
        if (detail["new_rupture_signal"] or detail["new_excess_signal"]
            or detail["max_rupture_rise_pp"] > rupture_rise_limit_pp + 1e-8
            or -diff["Fill rate (%)"] > fill_drop_limit_pp + 1e-8):
            continue
        if standard_assumptions:
            strict = tcc_check(res, plan, base_signals)
            if (strict["new_rupture"] or strict["new_excess"] or
                strict["max_rupture_rise"] * 100 >
                min(rupture_rise_limit_pp, 100 * AUMENTO_MAX_RUPTURA) + 1e-8):
                continue
        reduction = -diff["Excedente no pior mês (un.)"]
        if reduction <= 1e-6:
            continue
        id_ = f"C{len(selected)+1}"
        cuts_text = " · ".join(
            f"{label(months[j])}: {(-p):+.1f}%".replace(".0%", "%")
            for j, p in zip(indices, cuts[i]) if p != 0
        )
        peak_index = int(detail["monthly"].loc[
            detail["monthly"]["Janela crítica"] &
            detail["monthly"]["Cobertura avaliável"],
            "Excedente simulado (un.)"
        ].idxmax())
        selected.append({
            "Cenário": id_,
            "Ajustes por lote": cuts_text,
            "Lotes alterados": int(detail["changed_lots"]),
            "Variação líquida (un.)": float(np.sum(plan - original)),
            "Excedente evitado no pior mês (un.)": float(reduction),
            "Maior excedente esperado (un.)": float(
                detail["simulated"]["Excedente no pior mês (un.)"]
            ),
            "Vendas perdidas adicionais (un.)": float(
                diff["Vendas perdidas na janela (un.)"]
            ),
            "Fill rate (%)": float(detail["simulated"]["Fill rate (%)"]),
            "Maior aumento ruptura (p.p.)": float(detail["max_rupture_rise_pp"]),
            "Mês de maior excedente": label(months[peak_index]),
        })
        plans[id_] = plan.copy()
        if len(selected) >= int(top_k):
            break

    return dict(
        candidates_checked=int(k), grid_size=int(space),
        eligible_lots=eligible,
        shortlist=pd.DataFrame(selected), plans=plans,
        n_admissible_screened=int(len(screening)), best=selected[0] if selected else None,
        reason="" if selected else (
            "Nenhuma redução foi admissível entre as combinações testadas "
            "com os limites selecionados. Manter o plano original ou reavaliar "
            "as premissas com o planejador."
        ),
        base_peak=base_peak, base_fill=base_fill,
        seed=int(seed), max_cut_pct=float(max_cut_pct),
        max_increase_pct=float(max_increase_pct),
        coverage_days=float(coverage_days),
        uncertainty_multiplier=float(uncertainty_multiplier),
    )
