"""Prioridades operacionais do Smart Launch, calculadas (sem inventar datas diárias).

Os prazos disponíveis no Triângulo são aproximações em competências mensais;
a data exata e a autorização de alteração dependem do sistema do fornecedor.
"""
import numpy as np

THRESHOLD = 0.025


def card_summary(product, res, close, threshold=THRESHOLD):
    """Resumo coerente com probabilidades e janela crítica da simulação.

    O risco principal é o evento do primeiro mês alertado; se os dois tipos
    ocorrerem juntos, usamos o mais provável naquele mês. O pico e a cobertura
    referem-se ao mesmo risco selecionado e à MESMA simulação.
    """
    months = list(res["months"])
    window = np.asarray(res["active"], dtype=bool)
    ex = np.mean(np.asarray(res["cov"]) >= 180, axis=0)
    ru = np.mean(np.asarray(res["lost"]) > 0, axis=0)
    events = []
    for j, month in enumerate(months):
        if not window[j]:
            continue
        for name, probability in (("Excesso", ex[j]), ("Ruptura", ru[j])):
            if float(probability) > threshold:
                events.append((j, month, name, float(probability)))
    if not events:
        return {
            "product": product, "alert": False,
            "model_scope": "Apenas janela crítica",
            "action": "Monitoramento",
            "message": "Sem gatilhos probabilísticos no período avaliado.",
        }
    events.sort(key=lambda x: (x[0], -x[3]))
    first_j, first_month, category, first_probability = events[0]
    matching = [event for event in events if event[2] == category]
    peak_j, peak_month, _, peak_probability = max(matching, key=lambda x: x[3])
    cover = float(np.median(np.asarray(res["cov"])[:, peak_j]))
    ltm = int(res["ltm"])
    relevant_lots = []
    for month, amount in zip(months, np.asarray(res["production"])):
        if float(amount) > 0 and month <= first_month:
            deadline = month - ltm
            relevant_lots.append({
                "month": month, "deadline": deadline,
                "changeable_by_lead_time": deadline > close,
                "amount": float(amount),
            })
    actionable = sorted(
        (lot for lot in relevant_lots if lot["changeable_by_lead_time"]),
        key=lambda x: x["deadline"]
    )
    if actionable:
        deadline = actionable[0]["deadline"]
        urgency = "Em prazo teórico"
        time_left_months = (deadline - close).n
        action = "Avaliar fornecedor"
        suggested = (
            "Avaliar redução ou adiamento do lote selecionável."
            if category == "Excesso" else
            "Avaliar reforço ou antecipação do abastecimento."
        )
        qualification = (
            "Alteração apenas tecnicamente simulável. "
            "Confirmar capacidade, contrato, lote mínimo e prazo real."
        )
        deadline_label = "Próximo prazo teórico"
    elif relevant_lots:
        deadline = max(lot["deadline"] for lot in relevant_lots)
        urgency = "Prazo teórico encerrado"
        time_left_months = None
        action = (
            "Avaliação comercial" if category == "Excesso"
            else "Monitorar e avaliar alocação"
        )
        suggested = (
            "Não há lote com prazo aberto que chegue até o primeiro risco. "
            "Avaliar encaminhamento comercial."
            if category == "Excesso" else
            "Não há lote com prazo aberto que chegue até o primeiro risco. "
            "Avaliar disponibilidade e alocação."
        )
        qualification = "Não apresentar mudanças de lote como executáveis."
        deadline_label = "Último prazo teórico"
    else:
        deadline = None
        urgency = "Sem lote planejado até o risco"
        time_left_months = None
        action = (
            "Avaliação comercial" if category == "Excesso"
            else "Monitorar e avaliar alocação"
        )
        suggested = (
            "Nenhum lote positivo chega até o primeiro risco. "
            "Avaliar alternativas comerciais."
            if category == "Excesso" else
            "Nenhum lote positivo chega até o primeiro risco. "
            "Avaliar alternativas de atendimento e alocação."
        )
        qualification = "Não foi possível identificar lote alterável na base."
        deadline_label = "Prazo de lote"
    return {
        "product": product, "alert": True, "type": category,
        "first_month": first_month, "first_probability": first_probability,
        "peak_month": peak_month, "peak_probability": peak_probability,
        "coverage_peak_days": cover, "deadline": deadline,
        "deadline_label": deadline_label, "urgency": urgency,
        "time_left_months": time_left_months, "action": action,
        "suggested": suggested, "qualification": qualification,
        "lead_time_months": ltm, "first_target_has_changeable_lot": bool(actionable),
    }
