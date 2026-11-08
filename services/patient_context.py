"""Isolamento do estado de interface, sem acesso ao banco ou regras clínicas."""

import secrets

# Somente autenticação e navegação sobrevivem à troca de prontuário.
# Uma lista de exclusões deixa novos widgets clínicos sem proteção por padrão.
CHAVES_GLOBAIS = (
    'user_email', 'autenticado', 'pagina', 'paciente', 'membro_ativo',
    'modulo_ativo', 'paciente_alvo',
)


def limpar_contexto_paciente(estado):
    """Remove IDs, payloads, hashes, rascunhos e widgets do prontuário anterior."""
    for chave in list(estado):
        if chave not in CHAVES_GLOBAIS:
            del estado[chave]


def preparar_contexto_paciente(estado):
    """Protege também trocas por URL/reconexão, antes de montar widgets clínicos."""
    paciente = estado.get('paciente')
    if estado.get('_paciente_contexto') != paciente or '_contexto_widgets' not in estado:
        limpar_contexto_paciente(estado)
        estado['_paciente_contexto'] = paciente
        estado['_contexto_widgets'] = secrets.token_hex(16)


def payload_do_paciente_ativo(payload, estado):
    """Sem paciente ativo ou com contexto divergente, nenhuma escrita é permitida."""
    paciente = estado.get('paciente')
    return (
        isinstance(payload, dict)
        and isinstance(paciente, str)
        and bool(paciente.strip())
        and payload.get('Paciente') == paciente
        and estado.get('_paciente_contexto', paciente) == paciente
    )


def chave_widget(estado, campo):
    """IDs de widgets sem chave original mudam a cada troca de prontuário."""
    return f"clinico:{estado['_contexto_widgets']}:{campo}"


def gravar_documento(db, colecao, estado, chave_id, dados):
    """Reserva a identidade antes da escrita para uma repetição usar o mesmo documento."""
    doc_id = estado.get(chave_id) or dados.get("Sessao_ID") or secrets.token_hex(16)
    estado[chave_id] = doc_id
    from google.api_core.datetime_helpers import DatetimeWithNanoseconds
    from google.api_core.exceptions import AlreadyExists, FailedPrecondition

    ref = db.collection(colecao).document(doc_id)
    versoes = estado.setdefault(chave_id + "_versoes", {})
    versao = versoes.get(doc_id)
    try:
        if versao:
            instante = DatetimeWithNanoseconds.from_rfc3339(versao)
            gravacao = ref.update(dados, option=db.write_option(last_update_time=instante))
        else:
            gravacao = ref.create(dados)
        versoes[doc_id] = gravacao.update_time.rfc3339()
    except (AlreadyExists, FailedPrecondition):
        atual = ref.get()
        registro = atual.to_dict() or {}
        if atual.exists and all(registro.get(k) == v for k, v in dados.items()):
            versoes[doc_id] = atual.update_time.rfc3339()
            return
        raise ValueError("O registro mudou em outra sessão. Reabra a ficha antes de salvar.")
