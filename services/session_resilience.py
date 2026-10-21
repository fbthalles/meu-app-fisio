"""
Módulo de Resiliência de Sessão, Wake Lock Mobile e Auto-Save Assíncrono - GENUA
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict

import streamlit as st
import streamlit.components.v1 as components


def injetar_wake_lock_mobile() -> None:
    """
    Injeta a Screen Wake Lock API (HTML5/JS) para manter a tela do smartphone/tablet
    acesa durante a avaliação clínica e envia ping periódico para manter a conexão ativa.
    """
    wake_lock_js = """
    <script>
    (function() {
        let wakeLock = null;

        async function requestWakeLock() {
            try {
                if ('wakeLock' in navigator) {
                    wakeLock = await navigator.wakeLock.request('screen');
                }
            } catch (err) {
                console.warn('WakeLock não pôde ser ativado:', err.message);
            }
        }

        // Solicita ao carregar e reativa se a aba voltar ao foco
        requestWakeLock();
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                requestWakeLock();
            }
        });

        // Heartbeat leve a cada 25s para evitar queda de WebSocket no mobile
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                window.dispatchEvent(new Event('resize'));
            }
        }, 25000);
    })();
    </script>
    """
    components.html(wake_lock_js, height=0, width=0)


def inicializar_estado_avaliacao(avaliacao_id: str, db_client: Any = None) -> None:
    """
    Inicializa o st.session_state['avaliacao_atual'] e restaura rascunho
    existente do Firestore caso a sessão tenha caído anteriormente.
    """
    if "avaliacao_id" not in st.session_state or st.session_state["avaliacao_id"] != avaliacao_id:
        st.session_state["avaliacao_id"] = avaliacao_id
        st.session_state["last_saved_hash"] = ""
        st.session_state["last_saved_time"] = None

        # Tenta recuperar rascunho salvo no Firestore
        if db_client is not None:
            try:
                doc_ref = db_client.collection("avaliacoes_rascunho").document(avaliacao_id).get()
                if doc_ref.exists:
                    st.session_state["avaliacao_atual"] = doc_ref.to_dict().get("dados", {})
                    return
            except Exception:
                pass

        if "avaliacao_atual" not in st.session_state:
            st.session_state["avaliacao_atual"] = {}


def atualizar_campo(chave: str, valor: Any) -> None:
    """
    Helper direto para atualizar qualquer campo da avaliação no session_state.
    """
    if "avaliacao_atual" not in st.session_state:
        st.session_state["avaliacao_atual"] = {}
    st.session_state["avaliacao_atual"][chave] = valor


def _gerar_hash_dados(dados: Dict[str, Any]) -> str:
    """Gera hash MD5 determinístico do dicionário para detectar mudanças reais."""
    serializado = json.dumps(dados, sort_keys=True, default=str)
    return hashlib.md5(serializado.encode("utf-8")).hexdigest()


@st.fragment(run_every="5s")
def monitor_autosave_firestore(db_client: Any, colecao: str = "avaliacoes_rascunho") -> None:
    """
    Fragmento autônomo que roda a cada 5 segundos em background.
    Salva no Firestore apenas se houver alteração real nos dados preenchidos.
    """
    avaliacao_id = st.session_state.get("avaliacao_id")
    dados_atuais = st.session_state.get("avaliacao_atual", {})

    if not avaliacao_id or not dados_atuais or db_client is None:
        return

    hash_atual = _gerar_hash_dados(dados_atuais)
    ultimo_hash = st.session_state.get("last_saved_hash", "")

    if hash_atual != ultimo_hash:
        try:
            payload = {
                "avaliacao_id": avaliacao_id,
                "status": "draft",
                "updated_at": datetime.now().isoformat(),
                "dados": dados_atuais,
            }
            db_client.collection(colecao).document(avaliacao_id).set(payload, merge=True)
            st.session_state["last_saved_hash"] = hash_atual
            st.session_state["last_saved_time"] = datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            st.caption(f"⚠️ Aguardando reconexão para salvar ({str(e)[:30]}...)")

    horario = st.session_state.get("last_saved_time")
    if horario:
        st.caption(f"🟢 Salvo automaticamente às {horario}")
