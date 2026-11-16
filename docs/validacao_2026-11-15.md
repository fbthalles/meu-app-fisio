# Validação do MVP — 15/11/2026

Continuação e fechamento da jornada oficial: [validação de 16/11](validacao_2026-11-16.md).

Base revisada: `825a931` (Antigravity). Etapas autorizadas: 1, 2, 3 e 5. A etapa 4, preparação para uso real, permanece adiada.

## Correções

- Novo registro preserva o ID em reruns e salvamentos repetidos. A regressão do commit base foi reproduzida para avaliação e check-in em banco em memória e corrigida sem remover a restauração dos widgets ao trocar de ficha.
- SANE mostra a série observada e a diferença em pontos percentuais. Removidas a curva arbitrária, as datas estimadas e as classificações de prognóstico derivadas dela.
- Checklist compartilhado por painel e laudo distingue medida ausente de meta não atingida. PASS desconhecido não vira resposta negativa. Derrame desconhecido não vira zero; `Nenhum` é uma medida válida de grau zero.
- Razão I:Q isométrica permanece calculada, sem aplicar faixa de normalidade isocinética. Metas GENUA não são apresentadas como bateria validada de alta.
- Insights de gestos descrevem achados, sem inferir diagnóstico ou prescrever exercícios a partir do gesto isolado. Variações de escores não confirmam relevância clínica automaticamente.
- Retiradas referências de MCID dos conjuntos adaptados KOOS, IKDC e LEFS na ficha; pontuações e registros existentes foram preservados.

## Evidências

- Suite: 86 testes via `.venv/bin/python -m unittest discover -s tests`.
- Antes da correção, o novo teste de ciclo de gravação falhava nas duas fichas por criar IDs diferentes. Depois, passou. AppTest dos formulários completos com banco em memória também preservou um documento após duas gravações.
- AppTest do painel com fixture sintética de 12 sessões: LSI 75%, SANE 85%, tolerância funcional 97%; seleção da primeira sessão sem exceção. Laudo gerado com LSI 75%.
- Medição pontual local em 14/11: painel 1,65 s, geração do laudo 0,42 s. Não é benchmark do Streamlit Cloud ou teste de carga.
- Aplicativo oficial em 14/11: acesso, busca do paciente de validação, restauração dos textos da avaliação e GROC inicial 0 confirmados. Avaliação inspecionada em viewport 390 × 844; tamanho restaurado depois.
- Laudo HTML atualizado inspecionado no navegador em 15/11: ADM com mostradores lado a lado e tamanho igual. Impressão física ainda não conferida.

## Limites e próximo fechamento

A jornada completa de criação, edição e recarga das sessões após este deploy ainda precisa de teste no aplicativo oficial. Não há certificação de uso clínico, auditoria integral dos questionários ou teste em aparelhos móveis físicos. Autenticação e preparação para pacientes reais seguem fora deste pacote. Não houve migração nem exclusão de dados.

## Fontes para a revisão da interpretação

- [Kyritsis et al., 2016](https://pubmed.ncbi.nlm.nih.gov/27215935/): razão I:Q avaliada em teste isocinético a 60°/s; não sustenta aplicar automaticamente o mesmo corte às forças isométricas em kgf do GENUA.
- [Consenso de Berna, 2016](https://bjsm.bmj.com/content/50/14/853): retorno ao esporte como decisão multifatorial. A lista de metas locais não substitui essa avaliação.

## Verificação após publicação

Publicados `795be1c` e `aa171d1`. No aplicativo oficial, uma sessão sintética foi gravada, reaberta no painel e editada, permanecendo S1. O teste encontrou perda do valor inicial de flexão ao voltar do painel para uma ficha recém-salva; `aa171d1` recupera o payload salvo e adiciona regressão específica. A verificação completa dessa última correção no Cloud permanece pendente; o teste local passou.
