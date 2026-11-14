# P1-A — isolamento do estado e bloqueio de payload descontextualizado

Branch `fix/isolamento-pacientes`, baseada na main após PR #2 (`da0a2bf`).
Esta entrega altera o código do aplicativo. Não é apenas documentação da auditoria.

## Mudanças

- Novo `services/patient_context.py`: limpeza compartilhada por ambos os caminhos
  de troca de paciente. Apenas autenticação e navegação sobrevivem; IDs, payloads,
  hashes, rascunhos, horários e chaves clínicas explícitas são removidos. Novas
  chaves globais precisam entrar conscientemente na lista de preservação.
- `streamlit_app.py` e `ui_dados_paciente.py` usam esse mesmo helper.
- Avaliação e check-in preparam o contexto antes dos widgets. Mudança de paciente
  por outra rota também descarta o estado anterior. Rerun do mesmo paciente mantém
  os campos em andamento.
- Inputs que não tinham chave explícita receberam chaves por contexto (61 na
  avaliação, 7 no check-in). Uma identidade aleatória transitória muda ao trocar
  paciente; nomes de pacientes não entram nesse identificador. As chaves existentes
  continuam sendo descartadas pela limpeza compartilhada.
- Ambos os fragmentos e os caminhos manuais de salvamento exigem payload associado
  ao paciente ativo. Sem paciente ou com contexto/payload divergente, retornam
  antes de gravar. Exibem indicação de bloqueio.
- `services/session_resilience.py` descarta o conteúdo do draft anterior antes de
  tentar recuperar o novo. Draft inexistente ou leitura malsucedida não reaproveita
  os dados do outro paciente.

Durante a validação, AppTest demonstrou que apenas limpar as chaves visíveis de
`session_state` não reseta widgets sem chave explícita. Por isso foram adicionadas
as chaves por contexto; o teste agora verifica campos com e sem chave original.
Não há alteração de perguntas, respostas, pesos, fórmulas ou limiares clínicos.

## Validação

```bash
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/meu-app-fisio/bin/python -m unittest discover -s tests -v
```

72 testes: **61 aprovados, 11 falhas conhecidas**, zero erros inesperados, zero
pulados. Quatro falhas da auditoria passaram a ser regressões aprovadas:
P1-03, P1-04, P1-05 e P1-14. Dez novos testes cobrem:

- preservação de autenticação/navegação e limpeza de campos não previstos;
- troca A→B→A;
- preservação de dados em reruns do mesmo paciente;
- payload sem paciente e payload de outro paciente;
- bloqueio nos dois fragmentos, inclusive com IDs de documentos presentes;
- preservação do documento A enquanto B cria seu próprio registro;
- presença das guardas nos caminhos manuais (verificação estrutural do AST);
- recuperação de draft com erro de leitura;
- widgets reais Streamlit via AppTest: preenchimento, rerun e troca de paciente;
- chaves explícitas em todos os inputs clínicos dos dois renders.

Testes usam somente dados fictícios e banco em memória. AppTest executa uma tela
mínima com os helpers reais, não o aplicativo conectado ao banco. TCP/IP é bloqueado;
nesse teste permite-se somente AF_UNIX para o socketpair interno do loop asyncio.
A mensagem de contexto ausente que AppTest emite no runner não é erro do aplicativo.

## Limites e publicação

Não houve acesso ao Firebase, alteração de registros/coleções ou deploy.
Não há migração de históricos nem mudança na associação por nome; homônimos,
autenticação, idempotência remota, conflitos simultâneos e os outros 11 problemas
conhecidos permanecem fora deste pacote. Bloquear payload divergente não é uma
substituição para autorização ou verificação remota de propriedade de documentos.
Os testes de paths manuais são estruturais, sem renderização integral dos formulários.

O pacote deve ser revisado em PR e validado em ambiente de homologação antes de
merge: o README informa que a main aciona deploy automático. A simples existência
do commit ou push desta branch não atualiza o aplicativo publicado.

---

# Alinhamento Clínico (P1-16, P1-17, P1-18, P1-19, P1-D) e Proteção de Edição/Auto-save (P1-22)

## Mudanças implementadas

1. **Isolamento de widgets ao alternar ficha nova vs. existente e proteção do Auto-save (`P1-22`)**:
   - `services/patient_context.py`: adicionado `reiniciar_widgets_ficha(estado, preservar=())` para descartar chaves de widgets anteriores e rotacionar `_contexto_widgets` ao alternar entre `"➕ Nova Avaliação"` / `"➕ Nova Sessão"` e registros existentes no seletor.
   - `modulo_avaliacao.py` e `modulo_checkin.py`: ao abrir um registro existente para consulta/edição, o hash base (`_ultimo_hash_autosave` / `_ultimo_hash_autosave_chk`) é inicializado com o payload carregado, evitando regravações automáticas redundantes durante simples visualização e garantindo que 100% dos campos salvos sejam carregados na interface.
2. **Unificação da Razão I:Q em `55% a 68%` (`P1-18`)**:
   - Padronizado o intervalo ideal de equilíbrio agonista:antagonista (`55% a 68%`) em `modulo_avaliacao.py`, `modulo_painel.py`, `ia_clinica.py` e `pdf_laudo.py`.
3. **Ponto neutro inicial do GROC no Check-in Diário (`P1-19`)**:
   - `modulo_checkin.py`: novas sessões iniciam a escala GROC (-7 a +7) em `0 (Igual / Sem Mudança)` em vez de pré-selecionar `+2` ou `+3`.
4. **Rotulagem explícita das versões dos PROMs (`P1-D`)**:
   - `modulo_avaliacao.py` e `pdf_laudo.py`: identificadas explicitamente as **Versões Clínicas Adaptadas GENUA** (`KOOS-12`, `LEFS-10`, `IKDC-5`, `WOMAC-15`) e mantidas `VISA-P` e `Lysholm` como escalas de `8 itens oficiais`.
5. **Janela temporal na análise de estagnação (`P1-16`) e rotulagem da curva SANE (`P1-17`)**:
   - `ia_clinica.py`: `analisar_estagnacao()` aceita `dias_janela` opcional e informa no parecer o intervalo em dias corridos das últimas 5 sessões quando há datas válidas.
   - `modulo_painel.py`: curva SANE rotulada como **Trajetória de Referência por Fenótipo**.
