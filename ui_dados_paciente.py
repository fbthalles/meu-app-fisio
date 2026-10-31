"""GENUA | Tela de Cadastro, Edição e Seleção de Paciente (Estilo Apple HIG)."""
from services.patient_context import limpar_contexto_paciente
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, date
from config import CORES_GENUA, titulo, secao, toast
from firebase_client import db, conn, invalidar_cache


def _ativar_wake_lock_mobile():
    """Mantém a tela do celular ativa (Wake Lock API) e envia heartbeat para não cair a sessão."""
    components.html(
        """
        <script>
        (function() {
            async function manterTelaViva() {
                try {
                    if ('wakeLock' in navigator) {
                        await navigator.wakeLock.request('screen');
                    }
                } catch (e) {}
            }
            manterTelaViva();
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible') manterTelaViva();
            });
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def _calcular_idade_exata(dt_nasc: date) -> int:
    """Calcula a idade exata em anos considerando anos bissextos (mês e dia)."""
    hoje = datetime.now().date()
    return hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))


def _parse_data_nasc(data_str: str) -> date:
    """Converte string DD/MM/YYYY ou YYYY-MM-DD em objeto date seguro."""
    if not data_str:
        return date(2000, 1, 1)
    s = str(data_str).strip()[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return date(2000, 1, 1)


def _limpar_contexto_paciente_anterior():
    """Descarta todo o estado clínico anterior e preserva autenticação/navegação."""
    limpar_contexto_paciente(st.session_state)


def render():
    _ativar_wake_lock_mobile()

    # Cabeçalho limpo estilo macOS / iPadOS
    st.markdown(f"""
        <div style='margin-bottom: 24px;'>
            <h1 style='margin-bottom: 4px;'>👤 Gestão de Pacientes</h1>
            <p style='color: {CORES_GENUA['texto_suave']}; font-size: 0.98rem; margin: 0;'>
                Selecione um prontuário ativo na nuvem ou registre um novo paciente para iniciar a avaliação.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # 1. LEITURA OTIMIZADA COM CACHE (via firebase_client) + FALLBACK SEGURO
    df_cad = pd.DataFrame()
    lista_nomes = []
    try:
        df_cad = conn.read("Cadastro")
        if not df_cad.empty and "Nome" in df_cad.columns:
            lista_nomes = sorted(
                list(set(df_cad["Nome"].dropna().astype(str).str.strip().tolist()))
            )
            lista_nomes = [n for n in lista_nomes if n]
    except Exception:
        try:
            docs = db.collection("Cadastro").stream()
            lista_nomes = sorted(
                list(set([doc.to_dict().get("Nome", "").strip() for doc in docs if doc.to_dict().get("Nome")]))
            )
        except Exception as e:
            st.warning(f"⚠️ Não foi possível carregar a lista de pacientes: {e}")

    # 2. CARD DE SELEÇÃO DE PACIENTE (Estilo Spotlight / Busca Apple)
    with st.container(border=True):
        c_sel, c_stat = st.columns([3, 1])
        with c_sel:
            opcoes_select = ["+ Novo Paciente"] + lista_nomes
            paciente = st.selectbox(
                "🔍 Buscar ou Selecionar Paciente",
                opcoes_select,
                index=0,
                help="Digite para filtrar pelo nome do paciente ou escolha '+ Novo Paciente'."
            )
        with c_stat:
            st.metric("Total na Base", f"{len(lista_nomes)}", "Pacientes")

    # Limite de 100 anos exatos conforme solicitado
    data_minima_100_anos = date(datetime.now().year - 100, 1, 1)

    # 3. MODO A: CADASTRO DE NOVO PACIENTE
    if paciente == "+ Novo Paciente":
        with st.container(border=True):
            secao(
                "📋 Identificação do Novo Paciente",
                "Preencha os dados basais, indicação e a hipótese diagnóstica de encaminhamento."
            )

            nome = st.text_input("Nome Completo *", placeholder="Ex: Gabriel Medina")

            c_cad1, c_cad2, c_cad3 = st.columns(3)
            with c_cad1:
                data_padrao = date(2000, 1, 1)
                dt_nasc = st.date_input(
                    "Data de Nascimento *",
                    value=data_padrao,
                    min_value=data_minima_100_anos,
                    max_value=datetime.today().date(),
                    format="DD/MM/YYYY"
                )
            with c_cad2:
                cpf = st.text_input("CPF", placeholder="000.000.000-00")
            with c_cad3:
                telefone = st.text_input("Telefone (WhatsApp)", placeholder="(11) 99999-9999")

            c_cad4, c_cad5 = st.columns(2)
            with c_cad4:
                email = st.text_input("E-mail", placeholder="paciente@email.com")
            with c_cad5:
                ocupacao = st.text_input("Atividade Ocupacional / Esporte", placeholder="Ex: Atleta Amador / Engenheiro")

            st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)

            secao(
                "🎯 Diagnóstico Clínico & Indicação (Triagem)",
                "O motor de IA Clínica usará o diagnóstico para calibrar o fenótipo (ex: Pós-LCA, Tendinopatia Patelar, Condromalácia, Menisco, Artrose)."
            )
            c_dx1, c_dx2 = st.columns([1.8, 1.2])
            with c_dx1:
                dx_clinico = st.text_input(
                    "Diagnóstico Clínico / Médico",
                    placeholder="Ex: Reconstrução de LCA, Tendinopatia Patelar, Condropatia Femoropatelar..."
                )
            with c_dx2:
                medico_indicador = st.text_input(
                    "🤝 Indicação",
                    placeholder="Ex: Dr. Felipe / Paciente João / Instagram / Demanda Espontânea"
                )

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            if st.button("💾 Salvar e Abrir Prontuário", width="stretch", type="primary"):
                nome_limpo = nome.strip()
                if nome_limpo == "":
                    st.error("⚠️ O Nome Completo é obrigatório para abrir o prontuário.")
                elif any(n.lower() == nome_limpo.lower() for n in lista_nomes):
                    st.warning(f"⚠️ Já existe um paciente cadastrado como **{nome_limpo}**. Selecione-o na barra de busca acima para abrir ou editar seu prontuário.")
                else:
                    with st.spinner("🔄 Sincronizando prontuário no Firebase..."):
                        try:
                            idade_calc = _calcular_idade_exata(dt_nasc)
                            novo_cad = {
                                "Nome": nome_limpo,
                                "Data_Nascimento": dt_nasc.strftime("%d/%m/%Y"),
                                "Idade": idade_calc,
                                "CPF": cpf.strip(),
                                "Telefone": telefone.strip(),
                                "Email": email.strip(),
                                "Cidade_Estado": "",
                                "Ocupacao": ocupacao.strip(),
                                "Diagnostico_Clinico": dx_clinico.strip(),
                                "Medico_Indicador": medico_indicador.strip(),
                                "Historia": "",
                            }

                            db.collection("Cadastro").add(novo_cad)
                            invalidar_cache("Cadastro")

                            _limpar_contexto_paciente_anterior()
                            st.session_state.paciente = nome_limpo
                            st.session_state.membro_ativo = "Joelho"
                            st.session_state.modulo_ativo = "Avaliação Inicial 🔎"
                            st.session_state.pagina = "painel_clinico"
                            st.query_params["pac"] = nome_limpo
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Falha crítica reportada pelo servidor: {e}")

    # 4. MODO B: PACIENTE EXISTENTE SELECIONADO (Card de Resumo + Edição Rápida de Cadastro)
    else:
        dados_pac = {}
        if not df_cad.empty and "Nome" in df_cad.columns:
            filtro = df_cad[df_cad["Nome"].astype(str).str.strip() == paciente]
            if not filtro.empty:
                dados_pac = filtro.iloc[-1].to_dict()

        # Recalcula a idade dinamicamente se houver Data_Nascimento válida
        dt_nasc_salva = dados_pac.get("Data_Nascimento")
        if dt_nasc_salva and str(dt_nasc_salva).strip():
            dt_parsed = max(_parse_data_nasc(str(dt_nasc_salva)), data_minima_100_anos)
            idade_exib = _calcular_idade_exata(dt_parsed)
        else:
            dt_parsed = date(2000, 1, 1)
            idade_exib = dados_pac.get("Idade", "—")

        dx_exib = dados_pac.get("Diagnostico_Clinico") or "Não informado na triagem"
        ocup_exib = dados_pac.get("Ocupacao") or "Não informada"
        tel_exib = dados_pac.get("Telefone") or "—"
        med_exib = dados_pac.get("Medico_Indicador") or "—"

        with st.container(border=True):
            st.markdown(f"""
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;'>
                    <div>
                        <span style='font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: {CORES_GENUA['secundaria']};'>
                            Prontuário Localizado
                        </span>
                        <h3 style='margin: 2px 0 0 0; color: {CORES_GENUA['texto_escuro']}; font-size: 1.45rem;'>
                            {paciente}
                        </h3>
                    </div>
                    <span style='background: rgba(16, 62, 85, 0.08); color: {CORES_GENUA['primaria']}; padding: 6px 14px; border-radius: 980px; font-weight: 600; font-size: 0.88rem;'>
                        {idade_exib} anos
                    </span>
                </div>
            """, unsafe_allow_html=True)

            c_info1, c_info2, c_info3, c_info4 = st.columns(4)
            with c_info1:
                st.caption("🎯 DIAGNÓSTICO DE TRIAGEM")
                st.markdown(f"**{dx_exib}**")
            with c_info2:
                st.caption("🏃 OCUPAÇÃO / ESPORTE")
                st.markdown(f"**{ocup_exib}**")
            with c_info3:
                st.caption("🤝 INDICAÇÃO")
                st.markdown(f"**{med_exib}**")
            with c_info4:
                st.caption("📱 CONTATO")
                st.markdown(f"**{tel_exib}**")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            # Expander para editar dados cadastrais sem precisar recriar o paciente
            with st.expander("✏️ Editar Dados Cadastrais / Diagnóstico de Triagem"):
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    ed_dt_nasc = st.date_input(
                        "Data de Nascimento",
                        value=dt_parsed,
                        min_value=data_minima_100_anos,
                        max_value=datetime.today().date(),
                        format="DD/MM/YYYY",
                        key="ed_dt_nasc"
                    )
                with ec2:
                    ed_tel = st.text_input("Telefone (WhatsApp)", value=str(dados_pac.get("Telefone", "") or ""), key="ed_tel")
                with ec3:
                    ed_ocup = st.text_input("Ocupação / Esporte", value=str(dados_pac.get("Ocupacao", "") or ""), key="ed_ocup")

                ec4, ec5 = st.columns([1.8, 1.2])
                with ec4:
                    ed_dx = st.text_input("Diagnóstico Clínico / Médico", value=str(dados_pac.get("Diagnostico_Clinico", "") or ""), key="ed_dx")
                with ec5:
                    ed_med = st.text_input("🤝 Indicação", value=str(dados_pac.get("Medico_Indicador", "") or ""), key="ed_med")

                if st.button("💾 Atualizar Cadastro", type="secondary", key="btn_salvar_ed_cad"):
                    with st.spinner("Atualizando ficha cadastral no Firebase..."):
                        try:
                            idade_nova = _calcular_idade_exata(ed_dt_nasc)
                            campos_atualizados = {
                                "Data_Nascimento": ed_dt_nasc.strftime("%d/%m/%Y"),
                                "Idade": idade_nova,
                                "Telefone": ed_tel.strip(),
                                "Ocupacao": ed_ocup.strip(),
                                "Diagnostico_Clinico": ed_dx.strip(),
                                "Medico_Indicador": ed_med.strip(),
                            }
                            docs_pac = list(db.collection("Cadastro").where("Nome", "==", paciente).stream())
                            if docs_pac:
                                for d_ref in docs_pac:
                                    db.collection("Cadastro").document(d_ref.id).update(campos_atualizados)
                            else:
                                campos_atualizados["Nome"] = paciente
                                db.collection("Cadastro").add(campos_atualizados)

                            invalidar_cache("Cadastro")
                            toast("Dados cadastrais atualizados com sucesso!", "success")
                            st.rerun()
                        except Exception as e:
                            toast(f"Erro ao atualizar cadastro: {e}", "error")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            if st.button("🚀 Abrir Prontuário Clínico", width="stretch", type="primary"):
                _limpar_contexto_paciente_anterior()
                st.session_state.paciente = paciente
                st.session_state.membro_ativo = "Joelho"
                st.session_state.pagina = "painel_clinico"
                st.query_params["pac"] = paciente
                st.rerun()
