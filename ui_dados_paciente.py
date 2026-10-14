"""GENUA | Tela de Cadastro e Seleção de Paciente (Estilo Apple HIG)."""
import streamlit as st
import pandas as pd
from datetime import datetime
from config import CORES_GENUA, titulo, secao
from firebase_client import db, conn, invalidar_cache


def render():
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

    # 3. MODO A: CADASTRO DE NOVO PACIENTE
    if paciente == "+ Novo Paciente":
        with st.container(border=True):
            secao(
                "📋 Identificação do Novo Paciente",
                "Preencha os dados basais e a hipótese diagnóstica de encaminhamento."
            )

            nome = st.text_input("Nome Completo *", placeholder="Ex: Gabriel Medina")

            c_cad1, c_cad2, c_cad3 = st.columns(3)
            with c_cad1:
                data_padrao = datetime(2000, 1, 1)
                data_minima = datetime(datetime.now().year - 100, 1, 1)
                dt_nasc = st.date_input(
                    "Data de Nascimento *",
                    value=data_padrao,
                    min_value=data_minima,
                    max_value=datetime.today(),
                    format="DD/MM/YYYY"
                )
            with c_cad2:
                cpf = st.text_input("CPF", placeholder="000.000.000-00")
            with c_cad3:
                telefone = st.text_input("Telefone (WhatsApp)", placeholder="(11) 99999-9999")

            c_cad4, c_cad5, c_cad6 = st.columns(3)
            with c_cad4:
                email = st.text_input("E-mail", placeholder="paciente@email.com")
            with c_cad5:
                cidade = st.text_input("Cidade e Estado", placeholder="Ex: São Paulo - SP")
            with c_cad6:
                ocupacao = st.text_input("Atividade Ocupacional / Esporte", placeholder="Ex: Atleta Amador / Engenheiro")

            st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)

            secao(
                "🎯 Diagnóstico Clínico (Triagem)",
                "O motor de IA Clínica usará este campo para calibrar o fenótipo (ex: Pós-LCA, Tendinopatia Patelar, Condromalácia, Menisco, Artrose)."
            )
            dx_clinico = st.text_input(
                "Diagnóstico Clínico / Médico",
                placeholder="Ex: Reconstrução de LCA, Tendinopatia Patelar, Condropatia Femoropatelar..."
            )

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            # Botão de Ação Principal (Pílula Apple)
            if st.button("💾 Salvar e Abrir Prontuário", width="stretch", type="primary"):
                if nome.strip() == "":
                    st.error("⚠️ O Nome Completo é obrigatório para abrir o prontuário.")
                else:
                    with st.spinner("🔄 Sincronizando prontuário no Firebase..."):
                        try:
                            idade_calc = (datetime.now().date() - dt_nasc).days // 365
                            novo_cad = {
                                "Nome": nome.strip(),
                                "Data_Nascimento": dt_nasc.strftime("%d/%m/%Y"),
                                "Idade": idade_calc,
                                "CPF": cpf.strip(),
                                "Telefone": telefone.strip(),
                                "Email": email.strip(),
                                "Cidade_Estado": cidade.strip(),
                                "Ocupacao": ocupacao.strip(),
                                "Diagnostico_Clinico": dx_clinico.strip(),
                                "Historia": "",
                            }

                            db.collection("Cadastro").add(novo_cad)
                            invalidar_cache("Cadastro")

                            st.session_state.paciente = nome.strip()
                            st.session_state.membro_ativo = "Joelho"
                            st.session_state.pagina = "painel_clinico"
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Falha crítica reportada pelo servidor: {e}")

    # 4. MODO B: PACIENTE EXISTENTE SELECIONADO (Card de Resumo Rápido estilo Apple Health)
    else:
        dados_pac = {}
        if not df_cad.empty and "Nome" in df_cad.columns:
            filtro = df_cad[df_cad["Nome"].astype(str).str.strip() == paciente]
            if not filtro.empty:
                dados_pac = filtro.iloc[-1].to_dict()

        idade_exib = dados_pac.get("Idade", "—")
        dx_exib = dados_pac.get("Diagnostico_Clinico") or "Não informado na triagem"
        ocup_exib = dados_pac.get("Ocupacao") or "Não informada"
        tel_exib = dados_pac.get("Telefone") or "—"

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

            c_info1, c_info2, c_info3 = st.columns(3)
            with c_info1:
                st.caption("🎯 DIAGNÓSTICO DE TRIAGEM")
                st.markdown(f"**{dx_exib}**")
            with c_info2:
                st.caption("🏃 OCUPAÇÃO / ESPORTE")
                st.markdown(f"**{ocup_exib}**")
            with c_info3:
                st.caption("📱 CONTATO")
                st.markdown(f"**{tel_exib}**")

            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

            if st.button("🚀 Abrir Prontuário Clínico", width="stretch", type="primary"):
                st.session_state.paciente = paciente
                st.session_state.membro_ativo = "Joelho"
                st.session_state.pagina = "painel_clinico"
                st.rerun()
