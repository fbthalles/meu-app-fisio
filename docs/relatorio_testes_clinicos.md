# GENUA — testes e correções de cálculos clínicos

Data: 31/10/2026. Branch: `test/calculos-clinicos`.
Base analisada: `416b384710f09b12c8fb5a0f265e02f490032604`.

## Atualização após autorização das correções

**35 testes aprovados, zero falhas esperadas, zero erros, zero testes pulados.**
Comando de execução permanece o registrado abaixo. Verificados também sintaxe
Python dos três módulos alterados e `git diff --check`.

Corrigidos na branch `test/calculos-clinicos`:

- Parsing exato dos tokens de pontos de IKDC/VISA-P: máximos agora retornam 100.
  Todas as opções desses campos têm testes individuais dentro dos métodos.
- SANE inicial zero preservado no motor e painel; ganho calculado a partir do zero.
- LSI rejeita ausentes, negativos e não finitos; flexão ausente não gera exceção.
- Histórico de estagnação considera somente medidas finitas. Menos de cinco
  medidas válidas retorna insuficiência, preservando a janela e MCID existentes.
- GROC exige inteiro entre −7 e +7, tanto no motor como no painel.
- Lista explícita vazia de PROMs respeitada nas duas telas.
- Referência de força zero aparece como N/D na avaliação, sem simular LSI zero.
- Em lateralidade bilateral/indefinida, extensão e flexão permanecem associadas
  ao mesmo membro para I:Q. Preservada a escolha da menor extensão como referência;
  removida a combinação de mínimos de músculos pertencentes a lados diferentes.
  Exemplo testado: direita Ext20/Flex30 e esquerda Ext40/Flex10 → I:Q 150% e 25%.

Não alterados pesos, fórmulas de normalização, MCID, limiares I:Q/alta ou versões
adaptadas dos instrumentos. A divergência de limiares I:Q segue documentada e
coberta por teste de caracterização, aguardando validação clínica. Também não
foram reinterpretados ou migrados PROMs legados sem metadados.

As correções atuam em novos cálculos/exibições. Nenhum registro histórico foi
reescrito ou recalculado em produção. Não foi acessado Firebase nem feito deploy.
O isolamento dos testes continua limitado ao descrito abaixo, sem validação de
sessão real ou fluxo completo da interface.

## Registro histórico da análise anterior às correções

O restante desta seção e das tabelas abaixo registra o diagnóstico inicial;
as oito falhas conhecidas descritas foram corrigidas conforme a atualização acima.

## Resultado executado

Python 3.13.5; pandas 3.1.0 e NumPy 2.5.4 no ambiente preparado.

```bash
cd /workspace/meu-app-fisio
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/meu-app-fisio/bin/python -m unittest discover -s tests -v
```

**29 testes executados: 21 aprovados, 8 falhas conhecidas reproduzidas
(`expectedFailure`), nenhum erro inesperado e nenhum teste pulado.** Há casos
parametrizados adicionais dentro dos métodos. Não confundir `OK (expected
failures=8)` com ausência de defeitos: o runner considera essas falhas esperadas.
Uma correção que faça um desses testes passar gera `unexpected success` e exige
remover a marcação para manter a suíte verde.

Não foram alteradas fórmulas, fontes da aplicação, dependências ou registros.
Não houve importação do cliente Firebase, acesso ao Firebase ou deploy.
Todos os dados são fictícios, criados em memória. Nenhuma credencial é necessária.

## Estratégia e limites

`tests/clinical_source.py` extrai e compila os nós AST do código real: funções,
constantes literais e blocos de questionários dentro de `render()`. Não há cópias
das fórmulas nos testes. Imports e inicializadores dos módulos da aplicação não
são executados. Questionários usam um substituto mínimo de widgets Streamlit;
o orquestrador usa um adapter de DataFrames em memória sem métodos de escrita.
A criação de sockets é bloqueada durante todos os testes. Blocos e atribuições
inline são selecionados por nome e devem ser únicos, evitando seleção silenciosa
após mudanças estruturais.

Isso permite testar aritmética sem inicializar Firebase nem alterar o código
clínico. Não valida renderização completa, persistência, permissões, autenticação,
PDF, autosave, sessão real do navegador ou a integração do SDK. O teste A→B→A
valida isolamento do orquestrador em memória, não comprova ausência de vazamento
em `st.session_state` na interface. Não foi calculada cobertura percentual; não
há alegação de cobertura integral dos três arquivos.

## Funções e trechos analisados/testados

| Arquivo | Função ou trecho | Verificações |
|---|---|---|
| `ia_clinica.py` | `calcular_lsi` | Quadríceps, isquiotibiais, I:Q em cada lado, zero, negativos, ausentes, NaN, limites 85/90 e LSI >100 |
| `ia_clinica.py` | `analisar_estagnacao` | Janela das últimas cinco sessões, direção de dor e função, MCID exato, insuficiência, score desconhecido e NaN |
| `ia_clinica.py` | `analisar_percepcao_metas` | SANE atual/base/ganho/distância, GROC, PASS, precedência de estados, ausentes, inválidos e base zero |
| `ia_clinica.py` | `analisar_paciente` | Adapter fictício, datas fora de ordem, dois pacientes com forças e SANE diferentes, alternância A→B→A, preservação das entradas |
| `modulo_avaliacao.py` | `_detectar_proms_legados` | Metadados explícitos, pontuação zero e divergência com o painel |
| `modulo_avaliacao.py` | `render`: `lsi_g`, `iq_dir`, `iq_esq`, `status_iq_d` | Aritmética inline, divisão por zero e divergências entre telas |
| `modulo_avaliacao.py` | `render`: blocos KOOS, IKDC, LEFS, VISA-P, Lysholm, WOMAC | Respostas mínimas/máximas; intermediárias onde aplicável; número de itens KOOS/LEFS/WOMAC; conversão LEFS para 80 |
| `modulo_painel.py` | `_calcular_lsi_seguro` | Direito, esquerdo, bilateral/indefinido, denominador zero e equivalência com o motor |
| `modulo_painel.py` | `_score_funcional_item` | Respostas categóricas, numéricas, override de dor, limites e não testado |
| `modulo_painel.py` | `_detectar_proms_preenchidos` | Metadados explícitos, pontuação zero e lista vazia |
| `modulo_painel.py` | `_calcular_curva_prognostica_sane` | Início/fim em 16 semanas, preenchimento do ausente pela base e preservação do DataFrame |

`_extrair_valor_prefixo`, `normalizar_diagnostico` e `analisar_bandeiras` também
executam como dependências do teste do orquestrador, sem cobertura específica
completa. `_mapear_inchaco` e `_extrair_chave_str` não recebem testes dedicados
nesta entrega.

## Erros matemáticos/de implementação comprovados

Os números esperados abaixo decorrem das escalas e operações declaradas pelo
próprio código, sem decidir qual instrumento científico deveria ser usado.

| Caso | Reprodução fictícia e resultado atual | Resultado esperado pelo contrato | Teste |
|---|---|---|---|
| IKDC: parsing de pontos | Dor 10, frequência `Nenhuma (10 pts)`, atividade 10 pts, função atual 10 → **60** | A soma declarada é (10+10+10+20)/50×100 = **100** | `test_bug_ikdc_best_responses_should_sum_100` |
| VISA-P: parsing de pontos | Seis respostas 10, esporte 10 pts e tolerância 30 pts → **60** | 60+10+30 = **100** | `test_bug_visap_best_responses_should_sum_100` |
| SANE inicial zero descartado | Base 0, atual 20 → base **30**, ganho **−10** | Base **0**, ganho **+20** | `test_bug_sane_zero_baseline_must_remain_zero` |
| NaN no LSI | Força lesada NaN, saudável 40 → valor NaN e classificação `risco` | Resultado indisponível, sem classificação válida | `test_bug_nan_lsi_must_be_unavailable` |
| Flexão ausente | Extensores 40/50, flexor lesado None, saudável 30 → `TypeError` | Isquiotibiais indisponível, sem quebrar análise | `test_bug_none_flexion_must_not_crash` |
| Histórico ausente | Cinco NaN para dor → `piora`, delta NaN | Não concluir piora sem medidas válidas | `test_bug_missing_history_must_not_look_like_deterioration` |
| Metadados PROM divergentes | `PROMs_Aplicados=[]`, LEFS 50 → avaliação `[]`, painel `['LEFS']` | Leitura consistente do mesmo registro | `test_bug_explicit_empty_proms_should_be_consistent` |
| GROC fora do domínio | GROC 99, SANE 90, PASS True → `meta_atingida` | Valor fora de −7…+7 não pode autorizar essa conclusão | `test_bug_groc_outside_scale_should_not_enable_goal` |

Causa dos dois primeiros erros: comparações como `"0 pts" in resposta` também
são verdadeiras para `"10 pts"` e `"30 pts"`. A verificação do zero ocorre antes
das demais. Nenhum desses defeitos foi corrigido nesta etapa.

## Inconsistências determinísticas de apresentação/regra

Dois testes de caracterização passam justamente por confirmar a divergência atual:

- I:Q 69%: avaliação mostra “Equilíbrio Ideal (55–65%)”, pois aceita até **70**;
  motor considera elevada acima de **68**. Mesmo no motor, 66–68 é descrito como
  equilibrado com alvo textual de 55–65. A divergência é demonstrável; qual faixa
  deve ser adotada depende de revisão clínica do protocolo de medição.
- Denominador saudável zero: avaliação exibe LSI **0%**, enquanto painel e motor
  retornam indisponível. Zero calculado e ausência de referência não expressam a
  mesma informação. O teste registra a diferença, sem eleger uma nova fórmula.

Inspeção adicional: inferência de PROMs legados exclui resultados que também
podem ser legítimos (KOOS/WOMAC 100, Lysholm 100, VISA-P 50, IKDC 75) e o painel
retém no máximo dois candidatos. Sem metadados explícitos, ausência e resultado
real podem ser indistinguíveis. Isso precisa de decisão de migração/modelagem;
a suíte não presume que todo registro legado foi realmente preenchido.

## Interpretações que precisam de validação científica

Esta entrega não é revisão sistemática nem validação dos instrumentos. Os testes
confirmam a implementação atual, não sua equivalência a versões oficiais.

- LEFS usa **10 atividades** e reescala para “80 pontos equivalentes”; verificar
  validade dessa adaptação e uso de MCID 9 pontos nesse escore.
- O bloco chamado KOOS-12 agrega os 12 itens em um percentual. Verificar seleção
  dos itens, domínios, transformação e compatibilidade com o MCID citado.
- IKDC é uma composição reduzida de itens e pesos; corrigir o parsing não garante
  equivalência ao IKDC oficial. WOMAC utiliza 15 itens (5+2+8) e inverte o sentido
  para 100=melhor. Verificar validade e nomenclatura dessas adaptações.
- Revisar opções/pesos do VISA-P e a clareza do sentido dos sliders de dor; testar
  a soma não valida a redação ou fidelidade ao instrumento.
- LSI ≥90, limiar I:Q, SANE ≥85, GROC ≥3 e ganho SANE ≥15 são regras atuais,
  não provas suficientes de alta clínica. Validar população, teste isométrico,
  ângulo, dispositivo e contexto pós-operatório.
- Estagnação usa apenas a diferença entre os extremos de cinco medidas válidas;
  não considera intervalo temporal, variabilidade ou trajetória intermediária.
  MCID e janela não foram validados externamente nesta tarefa.
- Curva SANE usa potência 0,75, meta mínima 85 e fallback de 16 semanas; ausência
  é preenchida pela base. Validar prognóstico e risco de parecer uma piora real.
- No lado bilateral/indefinido, o orquestrador escolhe mínimos/máximos de extensão
  e flexão independentemente. Com forças cruzadas, a razão I:Q pode combinar lados
  físicos diferentes. Exige especificação da lateralidade antes de corrigir.

## Próximas etapas sugeridas (sem execução nesta entrega)

Corrigir parsing IKDC/VISA-P e preservação do zero SANE em tarefa separada;
validar domínios e ausentes; unificar regras duplicadas com aprovação clínica.
Depois, adicionar testes de sessão Streamlit com adapter fictício para troca de
pacientes, edição e autosave. Nenhuma dessas mudanças ou publicação foi feita.
