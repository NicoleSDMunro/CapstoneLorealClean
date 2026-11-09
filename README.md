# Smart Launch — Painel Operacional (TCC L'Oréal)

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
