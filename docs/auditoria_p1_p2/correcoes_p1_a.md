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
