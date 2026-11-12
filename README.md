# Smart Launch — Central de Alertas (interface clara, novembro/2026)

**Execute:** `streamlit run app.py`. A interface atual usa **seis áreas** em menu lateral e só apresenta valores calculados a partir do Triângulo carregado. O app original de quatro/cinco abas foi preservado em `smartlaunch_app.py`, enquanto o motor compartilhado foi extraído para `smartlaunch_core.py`.

## O que mudou nesta versão

1. **Central de Alertas:** indicadores reais dos três produtos, cards sincronizados com os gráficos, classificação de risco e ação, linha do tempo E/R/P restrita à janela crítica.
2. **Atualização mensal:** upload do Excel, auditoria dos blocos, fechamento/revisão comum aos produtos, diagnóstico de falhas e nenhuma simulação inventada quando a amostra é insuficiente.
3. **Previsão e modelos:** ranking experimental de quatro métodos (MEA-P, MEA, Oficial, Naive), seleção e modelo operacional separados, aprovação explícita da troca.
4. **Riscos de estoque:** gráficos de excesso e ruptura com linha de 2,5%, tabela por mês e evolução retrospectiva do risco para um mesmo mês-alvo quando há fechamentos avaliáveis.
5. **Simulador de decisões:** destaque para prazo teórico do lote; cortes/adiamentos/antecipações só aparecem quando o lote está dentro do prazo. Com prazo vencido, a tela orienta encaminhamento comercial ou monitoramento, sem oferecer redução como ação executável.
6. **Histórico e metodologia:** parâmetros de sensibilidade, registro temporário de aprovações e exportação de riscos CSV.

## Atenção antes de usar com a L'Oréal

- **Não é homologado para produção:** reproduzir previsões, cenários, coberturas e gatilhos contra o notebook final e o Excel de resultados é obrigatório.
- **Ranking reduzido e provisório:** os quatro candidatos e a elegibilidade simplificada não equivalem aos 49 modelos testados no TCC.
- **Sem persistência corporativa:** uploads e decisões duram somente a sessão Streamlit; sem controle de acesso, histórico entre sessões ou notificações externas.
- **Repositório público:** **não inserir planilhas reais no GitHub**. Qualquer implantação com dados reais exige um ambiente protegido autorizado. O processamento ocorre no servidor da aplicação.
- Os prazos calculados são teóricos (lead time), não garantia de viabilidade contratual.

## Testes

```bash
pip install -r requirements.txt
python -m py_compile app.py smartlaunch_core.py smartlaunch_ui.py smartlaunch_monthly.py
python tests/test_alert_rules.py
python tests/test_monthly.py
python tests/test_smoke.py
python tests/test_ui.py
```

---

# Smart Launch — Painel mensal de apoio à decisão (implementação incremental)

## O que está implementado nesta branch
- Upload do triângulo e leitura das revisões de PV, produção e estoque na **sessão Streamlit**, sem commit de dados empresariais.
- Seleção de produto e competência; previsões MEA/MEA-P/Oficial e Naive.
- **Nova aba Modelos:** backtest com origem rolante h1–h3 em pares comparáveis; MAPE, MAE, RMSE, viés, contagem de previsões, origens e meses-alvo; indicação de vencedor experimental.
- **Modelo operacional separado do vencedor estatístico**: aprovação explícita, com histórico apenas na sessão e opção de restaurar o modelo original.
- Simulação de 1.000 demandas Normal(0,s) e alternativa bootstrap centralizado, com erros históricos conhecidos; estoque, cobertura futura, probabilidades, gatilhos e simulação de lotes.
- Exportação CSV dos riscos mensais e auditoria dos blocos por produto.

## Limites importantes antes de homologar com a L'Oréal
1. **Ranking ainda não é o algoritmo definitivo do notebook**: são quatro candidatos (MEA-P, MEA, Oficial, Naive) e uma elegibilidade complementar (ao menos 3 previsões em 2 origens). A seleção definitiva do TCC tinha 49 modelos e regras específicas. Antes de usar a escolha operacional como evidência, confrontar e substituir este ranking pelo protocolo do `SmartLaunch_TCC_final.ipynb`.
2. Esta implementação **não possui persistência entre sessões**. A cada execução o usuário deve carregar o Excel novamente; versões passadas devem estar contidas no triângulo carregado. Aprovações registradas em memória não são um registro corporativo.
3. Ainda não foram implementados controle de acesso, armazenamento privado, trilha de auditoria permanente, relatórios PDF, notificação automática nem onboarding de produtos arbitrários.
4. Paridade do motor de previsão/risco com o notebook do TCC **não foi certificada**. Não usar em decisões de abastecimento sem homologação.
5. Alterações em lotes são simulações teóricas e dependem de contratos, capacidades e confirmação da L'Oréal.
6. O repositório é **público**: nunca commitar dados reais. Mesmo com processamento em memória, o upload trafega pelo servidor Streamlit; use apenas implantação autorizada e protegida para dados reais.

## Rodar
```bash
pip install -r requirements.txt
streamlit run app.py
python tests/test_smoke.py
python tests/test_monthly.py
python tests/test_ui.py
```

## Atualização mensal
Carregue o arquivo do novo fechamento na aba **Atualização mensal**. Selecione a revisão e o produto. O sistema recalcula o ranking dos candidatos elegíveis usando apenas alvos realizados até o fechamento selecionado. O modelo operacional aprovado permanece em uso até uma troca expressamente autorizada na aba **Modelos**. A nova previsão alimenta os cenários, os riscos e o simulador de lotes.

## Próximos passos obrigatórios
- Conectar e validar integralmente o notebook final e seus resultados, especialmente o backtest de 49 modelos, definição do período de arranque e amostragem dos erros.
- Integrar armazenamento seguro de versões mensais e decisões com autenticação e controle de acesso.
- Criar visão consolidada de todos os produtos, prazos finais de intervenção, relatório PDF/Excel e avaliação retrospectiva de alertas.
- Validar novos produtos, novos formatos de arquivo e cobertura de competências após dezembro de 2026.

---

# Smart Launch — Painel Operacional (TCC L'Oréal)

## Navegação — quatro áreas

1. **Visão geral:** previsão do modelo fixo, faixa probabilística, estoque, cobertura, gatilhos e primeiro mês prioritário.
2. **Simulador de decisões:** lotes alteráveis pelo lead time, efeitos de manter/reduzir/cancelar/adiar/antecipar, ajuste de 5% em 5% e encaminhamento comercial/fornecedor/monitoramento.
3. **Atualização de dados:** upload do triângulo (sem commit), auditoria PV/produção/estoque, seleção de produto e fechamento e histórico conhecido.
4. **Metodologia e histórico:** fórmulas, premissas, limitações, sensibilidade Normal × bootstrap centralizado e exportação de resultados.

**Execução:** `streamlit run app.py` e carregar o triângulo atualizado na aba Atualização de dados. O app começa sem números fictícios.

**Importante:** o teste de interface usa planilha sintética e verifica o funcionamento básico, não a calibração nem a paridade numérica com o notebook do TCC. A decisão final continua sendo humana.


Aplicativo Streamlit para análise mensal de lançamentos (metodologia consolidada em novembro de 2026).

## Uso
1. Instale as dependências: `pip install -r requirements.txt`.
2. Execute: `streamlit run app.py`.
3. Faça upload **na própria aplicação** do arquivo `Triangulo_Produtos_V2.xlsx` (não inclua dados reais no GitHub).
4. Escolha produto e revisão mensal. O fechamento usado corresponde ao mês anterior à revisão.
5. Observe previsão, P2,5/P50/P97,5, estoque, cobertura, alertas e alternativas em lotes fora do lead time.

## Lógica implementada
- P1: MEA-P; P2: MEA, seleção provisória; P3: plano Oficial.
- Realizado: mês `m` obtido da revisão `m+1`; nenhuma venda posterior ao fechamento é usada nas previsões.
- MEA e MEA-P: analogia com média de log10; MEA-P ajusta os meses de pipe M1–M3 com benchmark global conhecido na data.
- Simulação: 1.000 cenários, erros `Normal(0, s)` da sacola de erros do arranque, limitado a demanda não negativa.
- Estoque com demanda perdida e cobertura por consumo futuro; limite de excesso 180 dias.
- Janela crítica: `ceil(LT_semanas*7/30) + ceil(cobertura_dias/30) + 1`.
- Gatilhos dentro da janela crítica: excesso se P97,5 da cobertura ≥ 180 dias; ruptura se P97,5 das vendas perdidas > 0.
- Lotes somente testados se além do lead time, com os mesmos cenários entre alternativas.
- Bootstrap centralizado e erros persistentes disponíveis **apenas para sensibilidade**.

## Atenção metodológica
Este painel é uma **implementação operacional inicial** baseada no notebook `SmartLaunch_TCC_final.ipynb`, não uma substituição do notebook nem uma certificação de paridade numérica. A interface calcula os erros rolantes da fase de arranque novamente; as diferenças de recorte/sacolas devem ser comparadas com a planilha de resultados do notebook antes de uso real. A classificação de ação é uma interpretação simplificada para triagem; não considera contratos, lotes mínimos, capacidades ou confirmação de modificabilidade pela L'Oréal.

Não se usa o banco A–P antigo: o novo painel espera o triângulo P1–P3 e seus análogos. Em fechamentos com menos de dois erros elegíveis a simulação fica desabilitada; não fabrica desvios-padrão.

**Confidencialidade:** o arquivo enviado é processado em memória na sessão Streamlit; configure a infraestrutura e controle de acesso adequados antes de disponibilizá-lo à L'Oréal. O repositório é público. Não faça commit das planilhas reais.

## Estado
Versão inicial do painel; requer homologação com `SmartLaunch_TCC_final_resultados.xlsx`, especialmente gatilhos e ações do P3, antes de operação empresarial.
