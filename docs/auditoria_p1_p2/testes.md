# Execução e rastreabilidade dos testes P1/P2

## Comando

```bash
cd /workspace/meu-app-fisio
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/meu-app-fisio/bin/python -m unittest discover -s tests -v
```

Sem nova dependência: `unittest`, `unittest.mock` e módulos padrão, além de
pandas/NumPy já exigidos pelo projeto. A execução não precisa de credenciais.
Nunca fornecer secrets Firebase para esta suíte. As classes de teste bloqueiam
criação de socket durante execução, além de usar AST e adapters em memória.

**Resultado: 62 executados; 47 aprovados; 15 falhas conhecidas; 0 erros inesperados;
0 pulados.** As 15 falhas NÃO são testes aprovados. `expectedFailure` torna explícito
que as correções ficam para segunda etapa; um futuro sucesso inesperado faz a
suíte falhar até que a anotação seja removida após revisão.

## Requisitos obrigatórios

| Cenário | Teste/evidência |
|---|---|
| LSI36/40=90% e I:Q24/40=60% | `test_required_bilateral_values_and_zero_denominator` e testes prévios `test_iq_and_hamstring_lsi` |
| Denominador zero | Mesmo teste; helpers de painel/avaliação na suíte anterior |
| Dor0 e teste não realizado | `test_p1_01_zero_pain_does_not_imply_performed_test` — falha conhecida |
| SANE ausente | `test_p1_02_absent_sane_is_not_observed_thirty` — falha conhecida; caracterização da imputação na curva |
| PROM não aplicado | `test_explicit_prom_not_applied_survives_legacy_values` — aprovado |
| Cinco sessões sem mudança, datas distintas | `test_five_sessions_different_dates_temporal_characterization` — aprovado como caracterização: horas e meses recebem a mesma classe; NÃO valida estagnação |
| Troca A/B | `test_patient_isolation_with_fake_adapter_and_unsorted_dates` anterior passa; P1-03/04/05/14 reproduzem problemas no estado/recuperação |
| Dois salvamentos consecutivos | Avaliação e check-in: mesmo payload salva uma vez e edição reutiliza ID; P1-06/07/11/15 expõem limites de retry, adapter e dois clientes |
| Leitura histórica | `test_legacy_parsers_are_read_only_and_accept_existing_formats` e `test_longitudinal_dates_sorted_with_legacy_records` passam para os formatos testados; P1-09/12 mostram ambiguidades |
| Limites/inconsistências | Suíte anterior: zeros, negativos, NaN/inf, GROC−7…7, SANE0…100, ausência de flexão, lado bilateral e todas as opções IKDC/VISA-P |

Cada `test_p1_NN_...` associa-se à linha de mesmo ID no relatório. O teste P1-03
falha já no payload remanescente; não constitui prova independente para cada chave
de widget. O P1-14 complementa com a sequência limpeza→autosave usando DB fictício.

Os testes de dois clientes intercalam chamadas sequenciais com estado independente
para demonstrar a falta de proteção contra escrita obsoleta; não são benchmark de
concorrência nem teste de transação real. Perda de confirmação é uma injeção de
falha determinística, não um erro observado na infraestrutura real.

## Limites de cobertura

Não validam DOM/layout, autenticação real, regras do Firebase, índices, SDK gRPC,
cache distribuído, WebSocket, app completo ou arquivo PDF renderizado. O stub de
`set(merge=True)` tem merge superficial suficiente para os payloads escalares desses
testes; não simula merge profundo e não serve para aprovar estratégias de conflito.
Não há percentual de cobertura de linhas/branches. Os 35 testes prévios mantêm a
regressão matemática e o isolamento do orquestrador nas condições simuladas.

`inventario_instrumentos.md` é um recorte documental congelado da base; não é
executado nos testes. Os cálculos dos testes sempre usam os nós AST atuais.

## Arquivos novos desta etapa

- `tests/audit_support.py`: UI/state e banco em memória, extração do adapter e do
  trecho longitudinal real; nenhum SDK ou segredo.
- `tests/test_audit_p1_p2.py`: 27 testes de auditoria, 15 com falha conhecida.
- `docs/auditoria_p1_p2/relatorio.md`: gravidade, impacto, plano e aprovações.
- `docs/auditoria_p1_p2/referencias.md`: matriz de fontes e bloqueio de verificação.
- `docs/auditoria_p1_p2/inventario_instrumentos.md`: itens/opções/fórmulas reais.
- `docs/auditoria_p1_p2/testes.md`: este roteiro.
- `docs/auditoria_p1_p2/resultados_testes.json`: resultados da execução atual.

Os arquivos de testes/documentação do PR #1 foram preservados.
