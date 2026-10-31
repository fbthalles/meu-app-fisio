# GENUA — auditoria P1/P2, primeira etapa

Data: 31/10/2026. Branch: `audit/p1-p2`.
Base: `613f7428cfc5399f8c833f7969b53bb1b5964278` (`main`, após PR #1).
README lido integralmente; nenhum AGENTS.md encontrado na busca em `/workspace`.

**Nesta etapa foram adicionados somente testes e documentação. Não foram alterados
arquivos do aplicativo, fórmulas, credenciais, coleções ou registros. Não houve
consulta ao Firebase, uso de pacientes reais, deploy, merge ou push para `main`.**
As correções do PR anterior já pertencem à base e não são novas mudanças desta etapa.

## Resultado e alcance

62 testes: **47 aprovados, 15 falhas conhecidas reproduzidas**, zero erros
inesperados e zero testes pulados. Os 35 testes anteriores continuam aprovados;
esta auditoria acrescenta 27 testes. As falhas conhecidas usam `expectedFailure`:
o status `OK (expected failures=15)` não significa segurança clínica aprovada.
Ver `testes.md` e `resultados_testes.json` para comandos e rastreabilidade.

Auditoria estática e testes de funções/trechos reais extraídos por AST. O fake
Firestore fica apenas na memória; a abertura de sockets é bloqueada nos testes.
A implementação clínica não é reescrita dentro dos testes. Não foram executados
os imports dos entrypoints nem o cliente real Firebase. O fake não reproduz
transações, consistência do SDK, deep merge de mapas nem latência real.

**Revisão científica externa incompleta:** PubMed e KOOS retornaram 403 do proxy.
As fontes e o estado de conferência estão em `referencias.md`. Há inventário
verificável do código, mas não há alegação de validação das versões oficiais,
traduções, MCID ou PASS. As adições de rede foram salvas no rascunho, sem aplicação
confirmada à máquina atual. Não se deve aprovar mudança de fórmula com base apenas
nesta comparação preliminar.

## Critérios de classificação

- **M — erro matemático confirmado:** operação produz resultado incompatível com
  seus próprios operandos/escala. As correções IKDC/VISA-P do PR #1 passam. Não foi
  encontrado novo erro de divisão/soma nos casos válidos desta bateria.
- **D — divergência de instrumento:** itens, pergunta, direção ou normalização
  adaptados. A diferença no código é observável; a comparação formal com a versão
  validada permanece pendente de documentos oficiais.
- **C — interpretação clínica questionável:** extrapolação de medida para conclusão.
- **E — evidência insuficiente:** justificativa específica não demonstrada; não
  confundir com comprovação de ineficácia.
- **T — problema técnico:** identidade, persistência, estado, ausência ou execução.

Gravidade: **crítica** se pode comprometer identificação/acesso ao prontuário;
**alta** se pode gerar conclusão clínica falsa ou perda/duplicação silenciosa;
**média** se prejudica rastreabilidade/desempenho sem dano demonstrado;
**baixa** se apenas apresentação. Prioridade não equivale a incidência medida:
nenhum evento em produção foi investigado.

## Inventário e comparação dos instrumentos

O arquivo `inventario_instrumentos.md` contém os itens, opções e fórmulas exatos,
extraídos dos seis blocos de `modulo_avaliacao.render()` na base auditada.

| Instrumento no app | Itens/respostas e fórmula implementada | Limites/direção | Comparação preliminar e impacto |
|---|---|---|---|
| KOOS-12 | 12 itens próprios; 0 extremo/sempre…4 nenhum/nunca; soma/48×100 | 0 pior…100 melhor | Estrutura deve ser cotejada com KOOS-12 (domínios e summary score) e não com KOOS completo. MCID 8–10 de outra versão não demonstrado |
| IKDC “ampliado” | Dor/alívio 0–10; frequência 0/2/4/7/10; atividade 0/3/6/10; função anterior coletada mas não entra; função atual 0–10 com peso2; soma/50×100, teto100 | 0 pior…100 melhor | Não representa automaticamente o formulário IKDC subjetivo completo; os 5 prompts e pesos são observáveis no código. MCID9 e categorias <60/<85 exigem validação dessa composição |
| LEFS “10 atividades” | 10 atividades×0–4; soma/40×100; percentual/100×80 arredondado a uma casa | 0 pior…100 melhor; 0…80 equivalentes | Reescala não recupera informação dos 20 itens do instrumento original. Não equiparar 80 equivalentes à medida oficial ou transportar MCID9 sem validação |
| VISA-P “oficial” | 6 sliders0–10; esporte0/4/7/10; tolerância0/7/15/30; soma | 0 pior…100 melhor | Soma máxima corrigida; redação/âncoras e ramificação do item esportivo devem ser confrontadas com formulário original. Categorias <50/<80 e MCID13 não ficam validadas pela soma |
| Lysholm | 8 domínios: mancar5, apoio5, travamento15, instabilidade25, dor25, inchaço10, escadas10, agachar5 | 0 pior…100 melhor | Estrutura mais próxima da escala conhecida, mas versão/tradução e todas as opções ainda precisam de conferência. Categorias <65/<84/<95 não são prova de alta |
| WOMAC | 5 dor+2 rigidez+8 função; 0 nenhuma…4 muito intensa; 100−soma/60×100 | 0 pior…100 melhor | Comparador clássico contém 17 itens de função; redução para8 e inversão de direção devem ser identificadas. Não comparável automaticamente com total bruto ou short form validada |

Severidade **alta, D/C/E** para apresentação dessas composições como instrumentos
“validados” ou equivalentes sem identificação da versão. `MCID` no motor contém
LEFS9, KOOS8, VISA_P13, Lysholm10, IKDC9; não há metadado obrigatório de versão ou
unidade. O motor procura evolução funcional em `SANE_Pct`, `LEFS`, `KOOS`, enquanto
a avaliação persiste `LEFS_Pct`/`KOOS_Pct`. Auditar contrato de unidades e campos
antes de aplicar limiares aos históricos.

Não substituir nem converter registros históricos nesta etapa. Na segunda etapa,
propor metadados aditivos de instrumento/versão/idioma/direção/unidade e presença
por item, mantendo leitura dos campos antigos. Histórico sem versão deve ser
identificado como tal, sem conversão retrospectiva presumida.

## Achados por arquivo/função

| ID | Local | Classe / gravidade | Evidência e impacto |
|---|---|---|---|
| P1-01 | `modulo_painel._score_funcional_item` | C/T, alta | Override dor0 retorna10 mesmo com “Não testado”. `10−dor` mede inverso da dor, não execução, força ou capacidade; marcador não avaliado pode virar melhor resultado |
| P1-02 | `ia_clinica._sane_valido`, `analisar_percepcao_metas`; painel/curva | T/C, alta | SANE ausente assume30; curva substitui NaN pela base e chama a série de “real”. Distinguir medido, ausente e estimado |
| P1-03 | `streamlit_app._limpar_estado_paciente_ativo` | T, crítica | Remove IDs mas conserva `_payload_avaliacao_atual`, `_payload_checkin_atual` e várias chaves de widgets. Estado e fragmentos não ficam vinculados a paciente/episódio de forma única |
| P1-04 | `ui_dados_paciente._limpar_contexto_paciente_anterior` | T, crítica | Outra lista incompleta; conserva payload/ativação de check-in. Dois caminhos de troca com listas diferentes favorecem comportamento inconsistente |
| P1-05 | `services.session_resilience.inicializar_estado_avaliacao` | T, crítica potencial | Ao mudar draftA→draftB sem rascunho remoto, `avaliacao_atual` de A é preservado. Helper não está ligado ao entrypoint principal; risco demonstrado no helper, não ocorrência confirmada no fluxo atual |
| P1-06 | `modulo_checkin._fragmento_autosave_checkin` | T, alta | Escrita `.add()` concluída com confirmação perdida e nova tentativa cria dois IDs. Hash local só é atualizado após resposta; não garante idempotência remota |
| P1-07 | Mesmo fragmento, dois clientes | T, alta | Duas instâncias sem ID local criam duas sessões para o mesmo evento lógico, mesmo contendo ID lógico no payload fictício; nenhuma deduplicação remota |
| P1-08 | Mesmo fragmento, bloco de exceção/indicador | T, alta | Exceção silenciada e legenda verde com horário antigo continuam após falha. Usuário pode acreditar que a versão atual foi salva |
| P1-09 | `modulo_checkin._categoria_antiga_para_dor_num` | T/C, alta | “Não testado”, desconhecido e ausente retornam `(0,False)`, equiparando ausência a sem dor. Retorno precisa representar presença sem apagar legados |
| P1-10 | `modulo_painel.render`, preprocessamento longitudinal | C/T, alta | Nenhum teste → `Func_Score=None`, mas `df_p['LSI']=100`. Nome LSI não corresponde a medida bilateral. Defaults de sono, extensão e inchaço também supõem normalidade |
| P1-11 | `firebase_client.FirebaseAdapter.update` | T, alta | Sempre `.add(última_linha)`. Duas chamadas iguais geram dois documentos. Função pública tem semântica de inserir, apesar de se chamar update; revisar consumidores antes de mudar |
| P1-12 | `modulo_painel.render`, datas; `ia_clinica.analisar_paciente` | T, alta | Check-in parser aceita DD/MM/YYYY; painel usa dayfirst=False e motor também não fixa dayfirst para evolução. 02/01 e 01/02 podem ordenar fora do calendário brasileiro |
| P1-13 | `modulo_painel.render`, coluna Dor | T/C, alta | Campo ausente/inválido vira0 por fillna. Checklist pode aceitar controle álgico com medida inexistente |
| P1-14 | Limpeza do entrypoint + fragmento de avaliação | T, crítica | Teste combinado: paciente ativo B, payload antigo A e ID removido; fragmento aceita payloadA e cria novo documentoA. Não valida payload/paciente ativo. Demonstra escrita descontextualizada, não prova mistura de pacientes em produção |
| P1-15 | Check-in/avaliação `.set(...,merge=True)` | T, alta | Dois clientes com mesmo ID escrevem sem revisão/transação. Simulação intercalada mostra que payload antigo sobrescreve valor recente; merge não é controle de conflito |
| P1-16 | `ia_clinica.analisar_estagnacao` e `analisar_paciente` | C/E, alta | Ordena datas, mas detector recebe só valores. Cinco registros horários e cinco mensais constantes recebem a mesma conclusão “estagnacao”. Tempo, versão e erro de medida não entram |
| P1-17 | `modulo_painel._calcular_curva_prognostica_sane`, render | C/E, alta | Exponente0,75, meta≥85, faixas±5 e fallback16 semanas são exibidos como PBE/prognóstico esperado; nenhuma validação dessa combinação demonstrada |
| P1-18 | Avaliação `status_iq_d/e`; motor `calcular_lsi` | C/E, alta | Avaliação aceita55–70, motor55–68, textos dizem55–65. Aritmética I:Q correta em entradas válidas não valida a faixa nem equivalência entre protocolos |
| P1-19 | `modulo_checkin.render` e avaliação/widgets | T/C, alta | GROC inicial preseleciona+2/+3 conforme número de sessões; SANE vem de baseline/última sessão; campos normais pré-selecionados não distinguem confirmação de default. SANE é formulado como alcance da meta pessoal, construto possivelmente diferente |
| P1-20 | `firebase_client._ler_paciente_cached`, cadastro e roteamento | T, crítica potencial | Associação por nome textual em vez de identificador estável: homônimos e renomeação têm risco estrutural. Sem consulta à produção não é possível afirmar incidência |
| P1-21 | `ui_login.render`, `routing.aplicar_roteamento` | T, crítica | Código aceita e-mail/senha apenas por presença e restaura autenticação por Base64 sem assinatura; token de paciente também é reversível. Não foi testado acesso real nem consultadas regras Firebase. README chama Base64 de criptografia; essa descrição é incorreta |
| P1-22 | `modulo_avaliacao.render` e fragmento | T, alta | Exibição de avaliação existente monta payload e habilita autosave por paciente/QP, sem dirty tracking explícito da ação do usuário. Mudanças de defaults/esquema podem regravar histórico durante visualização; investigar em teste de integração antes de alterar |
| P2-01 | Consultas e `invalidar_cache` | T, média | Cache60s útil, mas avaliação/cadastro também fazem stream direto; invalidação ignora coleção e limpa todos os caches. Autosave frequente pode causar leituras repetidas entre usuários |
| P2-02 | Imports/render/PDF/gráficos | T, média | Matplotlib/PDF importados e PDF preparado no rerun da avaliação; tabs não garantem execução sob demanda. Painel cria vários gráficos em cada render. `plt.close` já é usado: não foi demonstrado leak |
| P2-03 | JS wake lock, reconexão | T, média | Evento resize não demonstra heartbeat de WebSocket ou persistência. APIs no iframe/mobile dependem de permissões/visibilidade; nenhuma medição real em dispositivo foi feita |
| P2-04 | `views/avaliacao.py` | T, média | Código de integração em nível de módulo usa `paciente_id`/`db` não definidos. Não importado pelo entrypoint atual; não é fluxo confiável para restaurar sessão |

As evidências P1-01…15 têm testes associados. P1-16 tem teste de caracterização
com cinco datas distintas em intervalos de horas e de30 dias. Os demais são
achados de inspeção estática e devem ser investigados em cenários de integração
com dados fictícios; não representam falhas remotas observadas.

## Dinamometria: o que foi e não foi validado

- Aritmética: LSI36/40=90%; I:Q24/40=60%; denominador zero indisponível;
  valores inválidos não são classificados nos helpers protegidos. Testes anteriores
  continuam passando. LSI acima100 é matematicamente possível com lado identificado.
- Rótulos kgf, músculos e lados estão disponíveis na avaliação. Não há contrato
  obrigatório e versionado de dispositivo, calibração, ângulo, alavanca, estabilização,
  número de tentativas e operador que garanta comparabilidade entre sessões.
- Lateralidade indefinida/bilateral usa menor/maior força. O PR anterior mantém I:Q
  no mesmo lado, mas isso não cria um membro “saudável” clinicamente conhecido.
- Parsers legados retornam0 para campo não encontrado e aceitam números sem
  protocolo. Falta de medição e força0 podem continuar indistinguíveis na ingestão.
- 85/90 e I:Q55–65/68/70 não foram validados nesta população/protocolo. O checklist
  tem seis critérios (não usa apenas LSI), mas não demonstra validação do conjunto.
  Nem LSI isolado nem a soma dos seis itens devem ser apresentados como decisão
  automática de alta sem aprovação e avaliação clínica contextual.

## P2: experiência desktop/tablet/smartphone

Inspeção do código, sem avaliação visual ou benchmark em navegadores reais.
Preservar cores, logo, tipografia e identidade existentes. Os seletores pills e
top navigation podem facilitar toque, mas não foram medidos cliques, responsividade,
contraste, tamanho de alvos, teclado móvel ou estabilidade com reconexão.

Plano de medição antes de otimizar: contar leituras/escritas por interação usando
fake instrumentado; medir reruns e duração de geração PDF/gráficos; cronometrar
cadastro→avaliação→check-in em desktop/tablet/smartphone com o mesmo roteiro fictício.
Testar viewport estreito, rotação, esconder/reabrir aba, perda/reconexão de WebSocket
e duas abas simultâneas. Não atribuir metas percentuais de desempenho sem baseline.

Priorizar dirty tracking, identidade estável do contexto, indicação “alterado /
salvando / confirmado / falha” e geração sob demanda de PDF/gráficos antes de
micro-otimizações. Cache por coleção/paciente e invalidação seletiva só depois de
assegurar atualização correta. Não persistir dados de pacientes em localStorage
como solução automática: requer revisão de privacidade e do modelo de sessão.

## Plano incremental para aprovação antes da segunda etapa

| Ordem | Pacote proposto | Pré-condição / aprovação | Aceite verificável |
|---|---|---|---|
| P1-A | Unificar limpeza e contexto de paciente/episódio; recusar payload descontextualizado; recuperação isolada | Aprovação técnica do fluxo/contrato; nenhuma migração executada | P1-03/04/05/14 passam; A→B→A e documento existente não alterado por troca |
| P1-B | Identidade estável e idempotência; versão de escrita e conflito; indicadores reais de salvamento | Definir o que identifica “mesma sessão” com responsável clínico; revisão de autenticação/acesso; compatibilidade com IDs existentes | P1-06/07/08/11/15 passam; timeout após commit remoto não duplica; conflito não perde versão silenciosamente |
| P1-C | Campos ausentes explícitos; separar dor, realização, capacidade e simetria; datas canônicas | Aprovação clínica da apresentação; decisão sobre legados sem metadados | P1-01/02/09/10/12/13 passam; nenhuma ausência vira normal; leitura de legados preservada |
| P1-D | Identificar instrumento/versão/idioma/unidade e revisar itens/limiares; distinguir SANE de meta pessoal | **Aprovação do responsável clínico após fontes oficiais e COSMIN** | Formulários e pesos conferidos; históricos rotulados sem reescrita automática; golden cases da versão aprovada |
| P1-E | Sinal de revisão longitudinal em vez de conclusão automática; curva claramente ilustrativa ou retirada | **Aprovação clínica** da terminologia, intervalo, erro de medida, versões e regras; sem novos limiares agora | Datas/ausências expostas; observado/estimado separados; nenhuma previsão individual validada presumida |
| P2-A | PDF/gráficos sob demanda, consultas seletivas, redução de reruns | P1-A/B estáveis e benchmark fictício documentado | Menos trabalho repetido medido, sem perda de campos/salvamento; gráficos fechados e cache coerente |
| P2-B | Roteiros responsivos e reconexão desktop/tablet/mobile | Ambiente isolado e política de sessão aprovada | Checklist de dispositivos executado com dados fictícios, recuperação e conflitos visíveis |

Decisões clínicas pendentes: versões oficiais versus adaptações; sentido das
escalas; tratamento de não realizado/incapaz; associação de SANE ao objetivo;
interpretação e protocolo do LSI/I:Q; MCID/PASS e janela temporal; critérios de alta;
rotulagem da curva; definição de nova sessão versus edição. Não foram criados
novos limiares nesta etapa. Correções de segurança e identidade também devem ser
revisadas tecnicamente; não dependem de inventar evidência clínica.

## Condições para encerrar a revisão científica

Concluir acesso e verificação das fontes na matriz; confirmar versões brasileiras
quando pertinentes; revisar os achados com responsável clínico e técnico. Não
está autorizado deploy ou alteração de produção. A etapa entregue torna os riscos
reproduzíveis; não equivale a liberar o sistema para novos protocolos clínicos.
