# Validação do MVP — 16/11/2026

Escopo: etapas 1, 2, 3 e 5. Etapa 4 adiada pelo responsável. Base inicial `ca7a1ce`, incluindo mudanças anteriores do Antigravity. Correções publicadas em `3d61944`.

## Correções encontradas na jornada

- Campos clínicos de avaliação e check-in recebem identidade por contexto de ficha. Na versão do Streamlit Cloud, apagar apenas o valor da sessão não recriava todos os controles: GROC, PASS, derrame e extensão podiam mostrar a resposta da ficha anterior. A correção abrange também campos bilaterais, perimetria, ADM e respostas dos questionários.
- Gravação manual seleciona o registro salvo; escolher Nova Sessão/Nova Avaliação passa a iniciar outro registro de forma explícita.
- Voltar à lista remove o paciente da URL. Recarregar a lista não reabre o prontuário anterior.
- Leitura de derrame compartilhada por painel e laudo; ausência e resposta desconhecida continuam diferentes de grau zero.
- SANE basal ausente aparece como não informado. Baseline zero não é substituído por 30 no check-in; evolução é expressa em pontos percentuais.
- GROC no check-in descreve melhora/piora percebida, sem declarar MCID universal. SANE 90% não declara objetivo totalmente alcançado.
- Removida inferência causal automática de sobrecarga ou amplificação central a partir da coincidência dor/derrame/sono. Texto de exportação e aba analítica usam metas de acompanhamento em vez de critérios universais de alta.

## Evidências

- 90 testes passaram: cálculos, medidas ausentes, zero válido, força unilateral, histórico, concorrência de gravação, contexto entre pacientes, identidade de documentos, navegação e isolamento de controles.
- Criado pela interface oficial o paciente `QA GENUA 16-11 — FICTÍCIO`, com história, objetivo, força bilateral, mobilidade, perimetria e Step Down (D) como gesto acompanhado. Avaliação datada de 14/11/2026.
- Duas sessões inseridas pela interface: 15 e 16/11. A primeira foi editada de flexão 110° para 115°, mantendo dois registros.

| Indicador | S1, 15/11 | S2, 16/11 |
|---|---:|---:|
| EVA diária | 6/10 | 0/10 |
| EVA semanal | 5/10 | 2/10 |
| Flexão | 115° após edição | 130° |
| Extensão | Déficit de 5° | Completa, 0° |
| Derrame | Leve, grau 1 | Nenhum, grau 0 |
| Dor no Step Down D | 6/10 | 2/10 |
| Tolerância calculada | 40% | 80% |
| SANE | 30% | 80% |
| GROC | 0 | +4 |
| PASS | Não | Sim |

- Dinamometria de avaliação: quadríceps 30/40 kgf e isquiotibiais 18/24 kgf, LSI 75% em ambos e razão I:Q 60% bilateral. O painel oficial mostrou LSI 75%, EVA 0, ADM 130°/0°, tolerância 80%, SANE 80% e GROC +4 em S2.
- Após publicação: alternar entre S1/S2 restaura derrame, extensão, GROC e PASS próprios, além das notas de dor e SANE. Recarga na lista permaneceu na lista.
- Troca entre dois pacientes fictícios, retorno ao caso atual e restauração dos indicadores confirmados no aplicativo oficial.
- Em viewport 390 × 844, navegação e cartões do painel ficaram dentro da largura disponível; laudo gerado pela interface mostrou flexão e extensão lado a lado, do mesmo tamanho, e sem tabela de sessões na ADM. Viewport restaurado após teste.
- Laudo oficial de S2 confirmou EVA zero, ADM 130°/0°, LSI 75%, ganho SANE de 50 pontos percentuais e GROC +4 separado.
- Selecionar S1 no painel e gerar novo laudo mostrou apenas o registro de Step Down 6/10 em S1, ADM 115°/déficit de 5°, SANE 30% e GROC 0. Nenhum valor de S2 entrou na conclusão histórica.
- Geração local do laudo de 12 sessões da fixture sintética: 0,392 s, HTML de 742.655 bytes (medição pontual, sem incluir rede ou impressão).

## Limites

Teste técnico com dados fictícios não equivale a validação clínica dos instrumentos ou certificação de segurança para uso real. Impressão física, aparelhos móveis físicos, teste de carga e etapa 4 continuam fora deste fechamento.
