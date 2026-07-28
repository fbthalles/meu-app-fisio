"""GENUA | Módulo 2: Check-in Diário (O Mutante)."""
import streamlit as st
from datetime import datetime
from config import CORES_GENUA, titulo
from firebase_client import conn, db

def render():
    st.markdown(f"<h3 style='color: {CORES_GENUA['primaria']};'>📝 Check-in Diário e Evolução</h3>", unsafe_allow_html=True)

    # 1. O "Caçador": Busca os testes definidos na Avaliação Inicial
    testes_para_hoje = ["Agachamento Bipodal"] # Valor de segurança caso haja falha
    try:
        docs_aval = db.collection("Avaliacao_Inicial").where("Paciente", "==", st.session_state.paciente).stream()
        lista_aval = [doc.to_dict() for doc in docs_aval]
        if lista_aval:
            ultima_aval = sorted(lista_aval, key=lambda x: x.get('Data_Avaliacao', ''))[-1]
            testes_para_hoje = ultima_aval.get("Testes_Alvo", ["Agachamento Bipodal"])
    except Exception:
        pass

    ## 2. Dados Basais da Sessão
    c_chk1, c_chk2 = st.columns(2)
    with c_chk1:
        data_sessao = st.date_input("Data da Sessão", datetime.now())
        eva_diaria = st.slider("EVA Diária (Dor Hoje)", 0, 10, 0)
        eva_semanal = st.slider("EVA Semanal (Média da Semana)", 0, 10, 0)
        inchaco_atual = st.selectbox("Inchaço / Derrame Articular", ["Nenhum", "Leve (+)", "Moderado (++)", "Intenso (+++)"])

    with c_chk2:
        adm_flex_atual = st.number_input("Flexão Máxima Atingida (Graus)", min_value=0, max_value=160, value=90)
        adm_ext_atual = st.selectbox("Extensão Terminal", ["Completa (0°)", "Déficit de -5°", "Déficit de -10° ou pior"])
        sono_atual = st.selectbox("Como dormiu esta noite?", ["Bem", "Acordou com dor", "Insônia"])

    # 3. Módulo Dinâmico de Testes Funcionais
    st.markdown("---")
    titulo("🎯 Relacional Funcional")
    st.caption("Classifique a relação entre dor e função para os testes definidos como alvo.")

    opcoes_escala = [
        "Sem Dor (0)",
        "Dor Leve (1 - 3)",
        "Dor Moderada (4 - 7)",
        "Dor Grave (8 - 10)",
        "Incapaz (Não realiza)"
    ]

    resultados_testes = {}
    for teste in testes_para_hoje:
        resposta = st.selectbox(f"Desempenho no {teste}:", opcoes_escala, key=f"chk_{teste}")
        resultados_testes[teste] = resposta

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Motor de Salvamento do Check-in
    if st.button("💾 REGISTAR SESSÃO DIÁRIA", width='stretch', type="primary"):

        # Pega o resultado do primeiro teste para compatibilidade com o Gráfico/PDF antigo
        texto_agachamento = list(resultados_testes.values())[0] if resultados_testes else "Não testado"

        dados_sessao = {
            "Data": data_sessao.strftime("%Y-%m-%d"),
            "Paciente": st.session_state.paciente,
            "Dor": eva_diaria,  # Mantivemos 'Dor' a apontar para a EVA Diária para não quebrar os gráficos que já existiam
            "EVA_Semanal": eva_semanal,
            "Flexao": adm_flex_atual,
            "Extensao": adm_ext_atual,
            "Inchaço": inchaco_atual,
            "Sono": sono_atual,
            "Testes_Funcionais": resultados_testes, 
            "Agachamento": texto_agachamento, 
            "Profissional_ID": st.session_state.get("user_email", "admin")
        }

        with st.spinner("A registar a sessão na nuvem..."):
            try:
                db.collection("Evolucao").add(dados_sessao)
                st.success("✅ Check-in diário registado com sucesso! Os gráficos e o PDF já foram atualizados.")
            except Exception as e:
                st.error(f"❌ Erro ao guardar os dados: {e}")
        
    st.write("---")
    with st.expander("⚖️ Conformidade LGPD e Privacidade"):
        st.caption("Processamento anonimizado de dados para finalidade exclusiva de Inteligência Clínica.")

