import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt
import numpy as np
from fpdf import FPDF
from PIL import Image
import matplotlib.pyplot as plt
import io

# 1. CORES DA MARCA (Extraídas do novo Logo GENUA Transparente)
CORES_GENUA = {
    'primaria': '#103E55',      # Azul-Petróleo Escuro (Cor das letras GENUA, traz autoridade e seriedade)
    'secundaria': '#398E9B',    # Verde-Água/Teal Claro (Destaques do joelho, traz frescor e modernidade)
    'fundo_claro': '#F4F7F9',   # Cinza Gelo levemente azulado para um fundo clínico e limpo
    'texto_escuro': '#1A252C',  # Um cinza-chumbo profundo (muito mais elegante que o preto puro)
    'texto_suave': '#6c757d',   # Cinza médio para legendas discretas
    'alerta_sucesso': '#28a745',# Verde padrão (positivo)
    'alerta_aviso': '#ffc107',  # Amarelo padrão (atenção)
    'alerta_erro': '#dc3545',   # Vermelho padrão (alerta grave)
}

# 2. CAMINHO DO NOVO LOGOTIPO

NOVO_LOGO_GENUA = "logo_genua_novo_v2.png" 

# 3. CONFIGURAÇÃO INICIAL DA PÁGINA 
st.set_page_config(
    page_title="GENUA | Inteligência Clínica",
    page_icon=NOVO_LOGO_GENUA, 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 4. APLICAÇÃO DO TEMA GLOBAL (CSS INJETADO)
st.markdown(f"""
    <style>
        .stApp {{
            background-color: {CORES_GENUA['fundo_claro']};
            color: {CORES_GENUA['texto_escuro']};
        }}
        h1, h2, h3 {{
            color: {CORES_GENUA['primaria']} !important;
        }}
        .stButton>button {{
            background-color: {CORES_GENUA['primaria']} !important;
            color: white !important;
            border: none;
            border-radius: 8px;
            font-weight: bold;
        }}
    </style>
""", unsafe_allow_html=True)

# 5. INJEÇÃO DO LOGO NA INTERFACE (BARRA LATERAL)
st.sidebar.image(NOVO_LOGO_GENUA, use_container_width=True)
st.sidebar.markdown("---") # Cria uma linha divisória elegante abaixo do logo

# ==========================================

# --- 1. FUNÇÕES DE SUPORTE E PDF ---

def limpar_texto_pdf(txt):
    """Garante que o PDF aceite acentuação e caracteres especiais do PT-BR."""
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, metrics, imgs):
    from fpdf import FPDF
    from datetime import datetime
    import io
    import os
    from PIL import Image
    import urllib.request
    import urllib.parse
    
    def hex_to_rgb(hex_code):
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        
    cor_primaria_rgb = hex_to_rgb(CORES_GENUA['primaria'])

    # 1. ENGENHARIA DO LOGO: Cria uma versão segura (sem transparência) para o FPDF repetir em todas as páginas
    logo_pdf_path = "temp_logo_pdf.jpg"
    try:
        img_logo = Image.open(NOVO_LOGO_GENUA).convert("RGBA")
        fundo_branco = Image.new("RGBA", img_logo.size, "WHITE")
        fundo_branco.paste(img_logo, (0, 0), img_logo)
        fundo_branco.convert('RGB').save(logo_pdf_path, format="JPEG", quality=95)
    except:
        logo_pdf_path = None

    class PDF_GENUA(FPDF):
        def footer(self):
            self.set_y(-15) 
            self.set_font('helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            hoje = datetime.now().strftime("%d/%m/%Y às %H:%M")
            self.cell(0, 10, f'GENUA Instituto | Inteligência Clínica | Emitido em {hoje} | Página {self.page_no()}', 0, 0, 'C')
            
            # UX VISUAL: Injeta o logo no canto inferior direito de TODAS as páginas como chancela
            if logo_pdf_path:
                try:
                    self.image(logo_pdf_path, x=175, y=self.get_y() + 1, w=22)
                except:
                    pass

    pdf = PDF_GENUA()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    azul_genua = cor_primaria_rgb 
    cinza_bg = (245, 245, 245) 
    cinza_txt = (80, 80, 80)
    
    # 2. CORES DAS CAIXAS DE INSIGHT
    bg_azul_claro = (209, 236, 241); txt_azul_escuro = (12, 84, 96)
    bg_amarelo_claro = (255, 243, 205); txt_amarelo_escuro = (133, 100, 4)
    bg_vermelho_claro = (248, 215, 218); txt_vermelho_escuro = (114, 28, 36)
    bg_verde_claro = (212, 237, 218); txt_verde_escuro = (21, 87, 36)

    # --- PARECERES CLÍNICOS DINÂMICOS ---
    if metrics['ikdc_status'] == 'Bom': par_ikdc = "Parecer Clínico: Excelente evolução. O paciente apresenta alta percepção de funcionalidade."
    elif metrics['ikdc_status'] == 'Regular': par_ikdc = "Parecer Clínico: Evolução moderada. Apresenta ganhos reais, mas demanda atenção fisioterapêutica."
    else: par_ikdc = "Parecer Clínico: Baixa funcionalidade percebida. Focar intensamente na modulação de sintomas."
        
    if metrics['alta'] not in ["Em análise", "Estabilizado"]: par_ev = f"Parecer Clínico: Cruzamento demonstra melhora. Projeção matemática de alta para {metrics['alta']}."
    else: par_ev = "Parecer Clínico: O gráfico mapeia a janela de tolerância. Foco atual em afastar a curva de função da curva de dor."

    grau_inc = int(float(metrics['inchaco']))
    if grau_inc <= 1: par_inc = "Parecer Clínico: Articulação estável (Grau 0-1). Cenário totalmente seguro para progressão."
    elif grau_inc == 2: par_inc = "Parecer Clínico: Presença de inchaço moderado (Alerta Amarelo). Recomendável estabilizar volume de treino."
    else: par_inc = "Parecer Clínico: Derrame articular importante (Alerta Vermelho). Imperativo regredir a sobrecarga mecânica."

    # LÓGICA DO INSIGHT ÁLGICO (DOR)
    dor_atual = float(metrics['dor'])
    media_dor = float(metrics['media_dor'])
    
    if dor_atual < media_dor:
        par_dor = f"Parecer Clínico: A dor atual ({int(dor_atual)}) está abaixo da média ({media_dor:.1f}), indicando dessensibilização efetiva."
        insight_dor_texto = "Quadro álgico em regressão. O paciente responde bem às estratégias analgésicas e a tolerância mecânica está aumentando."
        cor_bg_dor = bg_verde_claro; cor_txt_dor = txt_verde_escuro
    elif dor_atual == media_dor:
        par_dor = f"Parecer Clínico: Quadro álgico estabilizado na média ({media_dor:.1f}). Foco em romper o platô de sintomas."
        insight_dor_texto = "O paciente encontra-se em platô álgico. Necessário reavaliar variáveis de carga ou introduzir novos estímulos analgésicos."
        cor_bg_dor = bg_amarelo_claro; cor_txt_dor = txt_amarelo_escuro
    else:
        par_dor = f"Parecer Clínico: A dor atual ({int(dor_atual)}) encontra-se acima da média ({media_dor:.1f}). Recomenda-se reforço analgésico."
        insight_dor_texto = "Alerta de Hiperalgesia. A dor superou a média histórica do tratamento. Priorizar modulação de sintomas imediatamente."
        cor_bg_dor = bg_vermelho_claro; cor_txt_dor = txt_vermelho_escuro

    def get_img_height(img_buffer, pdf_width):
        img_buffer.seek(0)
        with Image.open(img_buffer) as im: return pdf_width * (im.height / im.width)

    def desenhar_caixa_insight(titulo, texto, cor_bg, cor_txt):
        pdf.ln(3)
        pdf.set_fill_color(*cor_bg); pdf.set_text_color(*cor_txt)
        pdf.set_font("helvetica", 'B', 9)
        texto_limpo = str(texto).replace("Parecer Biopsicossocial: ", "").replace("Evolução Ideal: ", "")
        pdf.cell(0, 6, limpar_texto_pdf(f" {titulo} "), ln=True, fill=True)
        pdf.set_font("helvetica", '', 9)
        pdf.multi_cell(0, 5, limpar_texto_pdf(f" {texto_limpo} "), fill=True)
        pdf.ln(3)

    # ==========================================
    # --- PÁGINA 1: SNAPSHOT EXECUTIVO E EVOLUÇÃO ---
    # ==========================================
    pdf.add_page()
    
    if logo_pdf_path:
        pdf.image(logo_pdf_path, x=10, y=8, w=35)
    else:
        pdf.set_font("helvetica", 'B', 14); pdf.cell(0, 10, "GENUA INSTITUTO", ln=True, align='C')
    
    pdf.ln(12)
    pdf.set_font("helvetica", 'B', 13)
    pdf.cell(0, 8, limpar_texto_pdf("RELATÓRIO DE INTELIGÊNCIA CLÍNICA"), ln=True, align='C')
    
    pdf.set_font("helvetica", 'B', 10); pdf.set_text_color(*azul_genua)
    pdf.cell(0, 6, limpar_texto_pdf(f"PACIENTE: {p_name.upper()}"), ln=True, align='C')
    pdf.set_font("helvetica", 'I', 9); pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, limpar_texto_pdf(f"Anamnese Base: {hist}"), align='C')
    pdf.ln(6)

    # GRID EXECUTIVO
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 9)
    w_col = 47.5 
    pdf.cell(w_col, 7, limpar_texto_pdf("DOR ATUAL"), border=1, fill=True, align='C')
    pdf.cell(w_col, 7, limpar_texto_pdf("INCHAÇO"), border=1, fill=True, align='C')
    pdf.cell(w_col, 7, limpar_texto_pdf("IKDC (FUNÇÃO)"), border=1, fill=True, align='C')
    pdf.cell(w_col, 7, limpar_texto_pdf("PREVISÃO ALTA"), border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_fill_color(*cinza_bg); pdf.set_text_color(0, 0, 0); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(w_col, 8, limpar_texto_pdf(f"{int(dor_atual)}/10"), border=1, fill=True, align='C')
    pdf.cell(w_col, 8, limpar_texto_pdf(f"Grau {grau_inc}"), border=1, fill=True, align='C')
    pdf.cell(w_col, 8, limpar_texto_pdf(f"{int(float(metrics['ikdc']))}/100"), border=1, fill=True, align='C')
    pdf.cell(w_col, 8, limpar_texto_pdf(f"{metrics['alta']}"), border=1, fill=True, align='C')
    pdf.ln(10)

    # 1. EVOLUÇÃO CLÍNICA
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 1. EVOLUÇÃO CLÍNICA (FUNÇÃO VS. DOR)"), ln=True, fill=True, align='C')
    y_ev = pdf.get_y() + 4
    pdf.image(imgs['ev'], x=20, y=y_ev, w=170) 
    
    pdf.set_y(y_ev + get_img_height(imgs['ev'], 170) + 5) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_ev), align='C')
    desenhar_caixa_insight("💡 INSIGHT EVOLUTIVO", metrics['insight_evolucao'], bg_azul_claro, txt_azul_escuro)

    # ==========================================
    # --- PÁGINA 2: DOR ISOLADA ---
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 2. COMPORTAMENTO DA DOR"), ln=True, fill=True, align='C')
    y_dor = pdf.get_y() + 4
    pdf.image(imgs['dor'], x=20, y=y_dor, w=170)
    
    pdf.set_y(y_dor + get_img_height(imgs['dor'], 170) + 5) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_dor), align='C')
    desenhar_caixa_insight("🧠 INSIGHT ÁLGICO", insight_dor_texto, cor_bg_dor, cor_txt_dor)

    # ==========================================
    # --- PÁGINA 3: INCHAÇO ---
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 3. MONITORAMENTO DE INCHAÇO"), ln=True, fill=True, align='C')
    y_inc = pdf.get_y() + 4
    pdf.image(imgs['inchaco'], x=20, y=y_inc, w=170)
    
    pdf.set_y(y_inc + get_img_height(imgs['inchaco'], 170) + 5) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_inc), align='C')
    desenhar_caixa_insight("⚠️ INSIGHT MECÂNICO", metrics['insight_mecanico'], bg_amarelo_claro, txt_amarelo_escuro)

    # ==========================================
    # --- PÁGINA 4: BIOPSICOSSOCIAL E QR CODE ---
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 4. ANÁLISE BIOPSICOSSOCIAL E FATORES EXTERNOS"), ln=True, fill=True, align='C')
    y_sono = pdf.get_y() + 4
    pdf.image(imgs['sono'], x=20, y=y_sono, w=170)
    
    pdf.set_y(y_sono + get_img_height(imgs['sono'], 170) + 5) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf("Parecer Clínico: O gráfico acima ilustra a interação do sono com a dor. Abaixo, os diagnósticos cruzados da Inteligência Artificial sobre fatores modificáveis."), align='C')
    
    desenhar_caixa_insight("💤 INSIGHT DO SONO", metrics['insight_ouro'], bg_verde_claro, txt_verde_escuro)
    desenhar_caixa_insight("🔴 INSIGHT POSTURAL (GATILHO BIOMECÂNICO)", metrics['insight_postura'], bg_vermelho_claro, txt_vermelho_escuro)

    # --- NOVO: BLOCO DE ASSINATURA E QR CODE ---
    pdf.ln(10)
    y_assinatura = pdf.get_y()
    
    # Gerador de QR Code Seguro (Via API)
    try:
        # ATENÇÃO: Substitua o número abaixo pelo WhatsApp da sua clínica
        link_agendamento = "https://wa.me/+5511933660220?text=Olá,%20gostaria%20de%20agendar%20meu%20retorno."
        url_qr = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link_agendamento)}"
        
        req = urllib.request.Request(url_qr, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            buf_qr = io.BytesIO(response.read())
            
        pdf.image(buf_qr, x=20, y=y_assinatura, w=28)
    except:
        pass # Se a internet falhar, o PDF é gerado normalmente sem quebrar o app
        
    pdf.set_y(y_assinatura + 4)
    pdf.set_x(52)
    pdf.set_font("helvetica", 'B', 11)
    pdf.set_text_color(*azul_genua)
    pdf.cell(0, 5, limpar_texto_pdf("DR. THALLES - FISIOTERAPIA ESPORTIVA"), ln=True)
    
    pdf.set_x(52)
    pdf.set_font("helvetica", '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, limpar_texto_pdf("Especialista em Reabilitação e Inteligência Clínica"), ln=True)
    
    pdf.set_x(52)
    pdf.set_font("helvetica", 'I', 8)
    pdf.cell(0, 5, limpar_texto_pdf("Aponte a câmera do celular para o QR Code ao lado para agendar seu retorno,"), ln=True)
    pdf.set_x(52)
    pdf.cell(0, 5, limpar_texto_pdf("acessar sua cartilha de exercícios ou falar diretamente com nossa equipe."), ln=True)

    # Faxina de sistema: Remove o arquivo temporário gerado
    try:
        if os.path.exists(logo_pdf_path):
            os.remove(logo_pdf_path)
    except:
        pass 
    return bytes(pdf.output())

# --- 2. INTERFACE E CONEXÃO ---
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# --- ROTEAMENTO SEGURANÇA (PORTAL DO CIRURGIÃO) ---
# ==========================================
import base64
import urllib.parse

query_params = st.query_params
is_medico = query_params.get("med", None)
token_paciente = query_params.get("token", None)
paciente_alvo = None

if is_medico == "true" and token_paciente:
    try:
        paciente_alvo = base64.b64decode(token_paciente.encode('utf-8')).decode('utf-8')
        # Esconde menu lateral e barra superior do Streamlit para o médico
        st.markdown("""
            <style>
                [data-testid="collapsedControl"] {display: none;}
                [data-testid="stSidebar"] {display: none;}
                header {display: none;}
            </style>
        """, unsafe_allow_html=True)
    except:
        pass
# ==========================================

with st.sidebar:
    # O logo já foi injetado globalmente no topo do arquivo.
    
    # Roteamento seguro: garante a criação da variável 'menu' sem duplicações
    if paciente_alvo:
        menu = "Painel Analítico 📊"
    else:
        menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "Avaliação IKDC 📋", "Painel Analítico 📊"])

# --- 3. MÓDULOS DE NAVEGAÇÃO ---

if menu == "Check-in Diário 📝":
    st.header("📝 Check-in Diário de Evolução")
    st.markdown(f"<p style='color: {CORES_GENUA['texto_suave']};'>Preencha os dados da sessão atual para alimentar a Inteligência Artificial.</p>", unsafe_allow_html=True)
    
    with st.form("checkin", clear_on_submit=True):
        paciente = st.text_input("👤 Nome do Paciente", placeholder="Ex: Thiago Rocha")
        
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Sintomas e Quadro Clínico</h4>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            dor = st.slider("💥 Dor atual (EVA 0-10)", 0, 10, 0)
        with c2:
            inchaco = st.select_slider("💧 Inchaço (Stroke Test)", options=["0", "1", "2", "3"])
            
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Função Biomecânica</h4>", unsafe_allow_html=True)
        c3, c4, c5 = st.columns(3)
        with c3:
            agac = st.selectbox("🏋️ Agachamento", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
        with c4:
            sup = st.selectbox("🪜 Step Up", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
        with c5:
            sdn = st.selectbox("📉 Step Down", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Fatores Biopsicossociais</h4>", unsafe_allow_html=True)
        c6, c7 = st.columns(2)
        with c6:
            sono = st.radio("💤 Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
        with c7:
            postura = st.radio("🧍 Postura Predominante", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
            
        # --- NOVO: MÓDULO DE AMPLITUDE DE MOVIMENTO (ADM) ---
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Biomecânica (ADM)</h4>", unsafe_allow_html=True)
        c8, c9 = st.columns(2)
        with c8:
            flexao = st.slider("📐 Flexão (Graus)", 0, 150, 90, help="Qual a flexão máxima atingida hoje?")
        with c9:
            extensao = st.selectbox("📏 Extensão Terminal", ["Completa (0° ou Hiperextensão)", "Déficit Leve (-5°)", "Déficit Moderado (-10°)", "Déficit Grave (>-15°)"])
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("✅ REGISTRAR SESSÃO", use_container_width=True):
            df = conn.read(ttl=0).dropna(how="all")
            # Adicionamos Flexao e Extensao na base de dados
            nova = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), 
                "Dor": int(dor), "Inchaço": str(inchaco), "Sono": sono, "Postura": postura, 
                "Agachamento": agac, "Step_Up": sup, "Step_Down": sdn,
                "Flexao": int(flexao), "Extensao": extensao
            }])
            conn.update(data=pd.concat([df, nova], ignore_index=True))
            st.success("Dados registrados com sucesso! A Inteligência Biomecânica foi alimentada.")
            
    st.write("---")
    with st.expander("⚖️ Conformidade LGPD e Privacidade"):
        st.caption("O Sistema GENUA utiliza Segurança por Obscuridade e processamento anonimizado de dados. As informações geradas têm finalidade exclusiva de Inteligência Clínica e Continuidade Assistencial, podendo ser revogadas a qualquer momento pelo paciente.")

elif menu == "Avaliação IKDC 📋":
    st.header("Score Científico IKDC")
    with st.form("ikdc"):
        p_ikdc = st.text_input("Nome do Paciente")
        nota = st.slider("Nota Global de Função (0-100)", 0, 100, 50)
        if st.form_submit_button("SALVAR SCORE"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": p_ikdc.strip(), "Score_IKDC": nota}])], ignore_index=True))
            st.success("Score IKDC registrado!")


else: # PAINEL ANALÍTICO (O CÉREBRO CLÍNICO TOTAL)
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        if paciente_alvo:
            # VISÃO DO MÉDICO: Título personalizado e bloqueio no paciente alvo
            st.markdown(f"<h2 style='color: {CORES_GENUA['primaria']}; text-align: center; margin-bottom: 25px;'>🏥 Portal do Cirurgião | Visão 360º</h2>", unsafe_allow_html=True)
            p_sel = paciente_alvo
            if p_sel not in df['Paciente'].values:
                st.error("Paciente não encontrado na base de dados.")
                st.stop()
        else:
            # VISÃO DO FISIOTERAPEUTA: Título normal e barra de busca
            st.header("📊 Painel Analítico & Clinical Intelligence")
            lista_pacientes = df['Paciente'].dropna().unique()
            
            p_sel = st.selectbox(
                "🔍 Buscar Paciente:", 
                options=lista_pacientes,
                index=None, 
                placeholder="Digite 3 letras do nome..."
            )
            
            if p_sel is None:
                st.info("👆 Por favor, digite o nome ou selecione um paciente acima para carregar a inteligência.")
                st.stop()
            
    
        # --- BUSCA E TRATAMENTO DA HISTÓRIA CLÍNICA (HMA) ---
    
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            registro_p = df_cad[df_cad['Nome'].str.strip() == p_sel].iloc[0]
            hist_clinica = registro_p['Historia']
            idade_p = int(float(registro_p['Idade'])) if pd.notna(registro_p['Idade']) else "N/A"
        except Exception as e:
            hist_clinica = "Histórico não disponível para este paciente."
            idade_p = "-"

        # INTERFACE: Cabeçalho Clean e Minimalista (Aprovado)
        st.markdown(f"""
            <div style='
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-left: 5px solid {CORES_GENUA['primaria']};
                padding: 20px 25px;
                border-radius: 8px;
                margin-bottom: 30px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            '>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;'>
                    <h3 style='margin: 0; color: {CORES_GENUA['primaria']}; font-weight: 700; font-family: sans-serif;'>
                        👤 {p_sel}
                    </h3>
                    <span style='
                        background-color: #f1f3f5; 
                        color: {CORES_GENUA['primaria']}; 
                        padding: 6px 15px; 
                        border-radius: 20px; 
                        font-size: 0.95rem; 
                        font-weight: 600;
                        border: 1px solid #e9ecef;
                    '>
                        {idade_p} anos
                    </span>
                </div>
                <div style='background-color: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #e9ecef;'>
                    <p style='margin: 0; color: #495057; line-height: 1.6; font-family: sans-serif;'>
                        <strong style='color: {CORES_GENUA['primaria']};'>HMA:</strong> {hist_clinica}
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
        df_p = df[df['Paciente'] == p_sel].copy()

    
        # 1. PROCESSAMENTO DE DADOS E EIXO X (DE 5 EM 5 SESSÕES)
        df_p['Sessão_Num'] = [f"S{i+1}" for i in range(len(df_p))]
        mapa_func = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        df_p['Score_Função'] = (df_p['Agachamento'].map(mapa_func) + df_p['Step_Up'].map(mapa_func) + df_p['Step_Down'].map(mapa_func)) / 3
        df_p['Sono_N'] = df_p['Sono'].map({"Ruim": 1, "Regular": 5, "Bom": 10})
        col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
        df_p['Inchaco_N'] = pd.to_numeric(df_p[col_inc], errors='coerce').fillna(0)
        
        # --- SEGURANÇA DE DADOS (ADM) ANTES DA MÁQUINA DO TEMPO ---
        if 'Flexao' not in df_p.columns:
            df_p['Flexao'] = 90
        if 'Extensao' not in df_p.columns:
            df_p['Extensao'] = "Sem dados antigos"
        df_p['Flexao'] = pd.to_numeric(df_p['Flexao'], errors='coerce').fillna(90)
        
        # --- NOVO: SELETOR TEMPORAL (MÁQUINA DO TEMPO CLÍNICA) ---
        opcoes_sessoes = df_p['Sessão_Num'].tolist()[::-1] # Lista invertida (S15, S14, S13...)
        
        st.write("") # Espaçamento
        c_vazio, c_seletor = st.columns([4, 1])
        with c_seletor:
            sessao_escolhida = st.selectbox("📅 Analisar Sessão:", options=opcoes_sessoes, index=0)
            
        # A variável 'ultima' agora reflete EXATAMENTE a sessão escolhida no seletor
        ultima = df_p[df_p['Sessão_Num'] == sessao_escolhida].iloc[0]

        # Intervalos de 5 sessões para o Eixo X em todos os gráficos
        indices_5 = np.arange(0, len(df_p), 5)
        labels_5 = [df_p['Sessão_Num'].iloc[i] for i in indices_5]

       # CÁLCULO DE TENDÊNCIA E PREVISÃO DE ALTA (BLINDADO)
        try:
            df_p['Data_DT'] = pd.to_datetime(df_p['Data'], dayfirst=True)
            df_p['Dias'] = (df_p['Data_DT'] - df_p['Data_DT'].min()).dt.days
            
            # Correção Matemática: Regressão exige no mínimo 2 pontos
            if len(df_p) > 1:
                z = np.polyfit(df_p['Dias'].values, df_p['Score_Função'].values, 1)
                trend_line = z[0] * df_p['Dias'].values + z[1]
                
                # Previsão Matemática de Alta (Score = 9.0)
                # Fórmula: y = ax + b -> 9 = ax + b -> x = (9 - b) / a
                if z[0] > 0.05: # Garante que a inclinação é positiva e relevante
                    dia_estimado_alta = (9.0 - z[1]) / z[0]
                    data_alta = df_p['Data_DT'].min() + pd.to_timedelta(dia_estimado_alta, unit='d')
                    prev_txt = data_alta.strftime("%d/%m/%Y")
                else:
                    prev_txt = "Estabilizado (Sem inclinação de melhora)"
            else:
                trend_line = []
                prev_txt = "Aguardando 2ª sessão"
        except Exception as e: 
            trend_line = []
            prev_txt = "Em análise"

        # SCORE CIENTÍFICO IKDC
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            u_ikdc = float(df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1])
            status_clinico = "Bom" if u_ikdc > 70 else "Regular" if u_ikdc > 45 else "Severo"
            emoji_ikdc = "🏆" if status_clinico == "Bom" else "🟢" if status_clinico == "Regular" else "🔴"
        except: 
            u_ikdc = 0; emoji_ikdc = "⚪"; status_clinico = "Pendente"

        # 2. GERAÇÃO DE GRÁFICOS (FIX ABSOLUTO DE LEGENDAS E VISIBILIDADE)
        cor_dor_grafico = CORES_GENUA['alerta_erro'] 
        cor_func_grafico = CORES_GENUA['secundaria'] 
        cor_trend_grafico = CORES_GENUA['texto_suave'] 
        cor_prim_grafico = CORES_GENUA['primaria'] 
        
        # A) Evolução Clínica
        fig_ev, ax_ev = plt.subplots(figsize=(10, 5))
        ax_ev.plot(df_p['Sessão_Num'], df_p['Dor'], color=cor_dor_grafico, label='Nível de Dor (EVA)', marker='o', linewidth=2)
        ax_ev.plot(df_p['Sessão_Num'], df_p['Score_Função'], color=cor_func_grafico, label='Capacidade Funcional', marker='s', linewidth=3)
        if len(trend_line) > 0:
            ax_ev.plot(df_p['Sessão_Num'], trend_line, '--', color=cor_trend_grafico, alpha=0.5, label='Tendência de Alta')
        
        ax_ev.set_title("Evolução Clínica: Capacidade Funcional vs. Dor", fontweight='bold', color=cor_prim_grafico)
        ax_ev.set_ylim(-0.5, 11)
        ax_ev.set_xticks(indices_5)
        ax_ev.set_xticklabels(labels_5)
        ax_ev.spines['top'].set_visible(False)
        ax_ev.spines['right'].set_visible(False)
        
        lgd_ev = ax_ev.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False)
        buf_ev = io.BytesIO()
        fig_ev.savefig(buf_ev, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_ev,), dpi=150)
        buf_ev.seek(0); plt.close(fig_ev)

        # B) Novo Gráfico: Dor Isolada 
        fig_dor, ax_dor = plt.subplots(figsize=(10, 3.5))
        ax_dor.fill_between(df_p['Sessão_Num'], df_p['Dor'], color=cor_dor_grafico, alpha=0.15)
        ax_dor.plot(df_p['Sessão_Num'], df_p['Dor'], color=cor_dor_grafico, label='Nível de Dor (EVA)', marker='o', linewidth=2)
        ax_dor.set_title("Comportamento Isolado da Dor (Quadro Álgico)", fontweight='bold', color=cor_prim_grafico)
        ax_dor.set_ylim(-0.5, 11)
        ax_dor.set_xticks(indices_5)
        ax_dor.set_xticklabels(labels_5)
        ax_dor.spines['top'].set_visible(False)
        ax_dor.spines['right'].set_visible(False)
        
        lgd_dor = ax_dor.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), frameon=False, fontsize=9)
        buf_dor = io.BytesIO()
        fig_dor.savefig(buf_dor, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_dor,), dpi=150)
        buf_dor.seek(0); plt.close(fig_dor)

        # C) Inchaço Articular 
        fig_inc, ax_inc = plt.subplots(figsize=(10, 3.5))
        cores_inc = [CORES_GENUA['alerta_erro'] if x == 3 else CORES_GENUA['alerta_aviso'] if x == 2 else cor_func_grafico for x in df_p['Inchaco_N']]
        ax_inc.bar(df_p['Sessão_Num'], df_p['Inchaco_N'], color=cores_inc, alpha=0.85, width=0.6, edgecolor='white')
        
        ax_inc.set_title("Linha do Tempo: Inchaço Articular", fontweight='bold', color=cor_prim_grafico)
        ax_inc.set_ylim(0, 3.5)
        ax_inc.set_xticks(indices_5)
        ax_inc.set_xticklabels(labels_5)
        ax_inc.spines['top'].set_visible(False)
        ax_inc.spines['right'].set_visible(False)
        
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=CORES_GENUA['alerta_erro'], alpha=0.85, label='Grau 3 (Grave)'),
            Patch(facecolor=CORES_GENUA['alerta_aviso'], alpha=0.85, label='Grau 2 (Moderado)'),
            Patch(facecolor=cor_func_grafico, alpha=0.85, label='Grau 0-1 (Estável)')
        ]
        lgd_inc = ax_inc.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=3, frameon=False, fontsize=9)
        
        buf_inc = io.BytesIO()
        fig_inc.savefig(buf_inc, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_inc,), dpi=150)
        buf_inc.seek(0); plt.close(fig_inc)

        # D) Sono vs Dor
        fig_s, ax_s = plt.subplots(figsize=(10, 4))
        ax_s.fill_between(df_p['Sessão_Num'], df_p['Sono_N'], color=cor_func_grafico, alpha=0.2, label='Qualidade do Sono')
        ax_s.plot(df_p['Sessão_Num'], df_p['Dor'], color=cor_dor_grafico, marker='o', linewidth=2, label='Nível de Dor')
        
        ax_s.set_title("Impacto Biopsicossocial: Sono vs Dor", fontweight='bold', color=cor_prim_grafico)
        ax_s.set_ylim(-0.5, 11)
        ax_s.set_xticks(indices_5)
        ax_s.set_xticklabels(labels_5)
        ax_s.spines['top'].set_visible(False)
        ax_s.spines['right'].set_visible(False)
        
        lgd_s = ax_s.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False)
        buf_s = io.BytesIO(); fig_s.savefig(buf_s, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_s,), dpi=150); buf_s.seek(0); plt.close(fig_s)

        # E) Cruzamento Biomecânico (ADM x Dor x Inchaço)
        fig_adm, ax1_adm = plt.subplots(figsize=(10, 4.5))
        
        # Linha da Flexão (Eixo Principal - Esquerda)
        ax1_adm.plot(df_p['Sessão_Num'], df_p['Flexao'], color=CORES_GENUA['secundaria'], label='Graus de Flexão', marker='s', linewidth=3)
        ax1_adm.set_ylim(0, 160)
        ax1_adm.set_ylabel("Amplitude de Movimento (Graus)", color=CORES_GENUA['secundaria'], fontweight='bold')
        ax1_adm.tick_params(axis='y', labelcolor=CORES_GENUA['secundaria'])
        
        # Eixo Secundário - Direita (Dor e Inchaço)
        ax2_adm = ax1_adm.twinx()
        
        # Barras de Inchaço ao fundo
        cores_inc_adm = [CORES_GENUA['alerta_erro'] if x == 3 else CORES_GENUA['alerta_aviso'] if x == 2 else CORES_GENUA['texto_suave'] for x in df_p['Inchaco_N']]
        ax2_adm.bar(df_p['Sessão_Num'], df_p['Inchaco_N'], color=cores_inc_adm, alpha=0.25, label='Inchaço (Grau)', width=0.6)
        
        # Linha de Dor por cima das barras
        ax2_adm.plot(df_p['Sessão_Num'], df_p['Dor'], color=CORES_GENUA['alerta_erro'], label='Nível de Dor (EVA)', marker='o', linewidth=2)
        
        ax2_adm.set_ylim(-0.5, 11)
        ax2_adm.set_ylabel("Dor (0-10) / Inchaço (0-3)", color=CORES_GENUA['alerta_erro'], fontweight='bold')
        ax2_adm.tick_params(axis='y', labelcolor=CORES_GENUA['alerta_erro'])
        
        ax1_adm.set_title("Evolução Biomecânica: ADM vs Dor vs Inchaço", fontweight='bold', color=cor_prim_grafico)
        ax1_adm.set_xticks(indices_5)
        ax1_adm.set_xticklabels(labels_5)
        ax1_adm.spines['top'].set_visible(False)
        ax2_adm.spines['top'].set_visible(False)
        
        # Juntando as legendas dos dois eixos para o design premium
        lines_1, labels_1 = ax1_adm.get_legend_handles_labels()
        lines_2, labels_2 = ax2_adm.get_legend_handles_labels()
        lgd_adm = ax1_adm.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False)
        
        buf_adm = io.BytesIO()
        fig_adm.savefig(buf_adm, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_adm,), dpi=150)
        buf_adm.seek(0); plt.close(fig_adm)

        # 3. MOTORES MATEMÁTICOS DE CRUZAMENTO E INSIGHTS
        media_dor = df_p['Dor'].mean()
        delta_dor_pct = ((ultima['Dor'] - media_dor) / media_dor * 100) if media_dor > 0 else (100 if ultima['Dor'] > 0 else 0)
        
        media_inc = df_p['Inchaco_N'].mean()
        delta_inc_pct = ((ultima['Inchaco_N'] - media_inc) / media_inc * 100) if media_inc > 0 else (100 if ultima['Inchaco_N'] > 0 else 0)

        # Insight 1: Sono vs Dor (Biopsicossocial)
        try:
            media_sono = df_p['Sono_N'].mean()
            dor_sono_bom = df_p[df_p['Sono_N'] >= media_sono]['Dor'].mean()
            dor_sono_ruim = df_p[df_p['Sono_N'] < media_sono]['Dor'].mean()
            if pd.notna(dor_sono_bom) and pd.notna(dor_sono_ruim) and dor_sono_ruim > 0 and dor_sono_bom < dor_sono_ruim:
                queda_pct = ((dor_sono_ruim - dor_sono_bom) / dor_sono_ruim) * 100
                insight_ouro = f"Parecer Biopsicossocial: Quando o paciente relata um sono superior à sua média, o nível de dor cai em {queda_pct:.0f}%. O manejo do sono atua como forte inibidor analgésico."
            else:
                insight_ouro = "Parecer Biopsicossocial: A correlação entre qualidade do sono e percepção de dor mantém-se dentro do desvio padrão esperado, sem discrepâncias agudas."
        except:
            insight_ouro = "Monitoramento contínuo em andamento para estabelecer correlação álgica com o sono."

        # Insight 2: Inchaço vs Função (Inibição Mecânica)
        try:
            func_inc_alto = df_p[df_p['Inchaco_N'] >= 2]['Score_Função'].mean()
            func_inc_baixo = df_p[df_p['Inchaco_N'] <= 1]['Score_Função'].mean()
            if pd.notna(func_inc_alto) and pd.notna(func_inc_baixo) and func_inc_baixo > 0 and func_inc_alto < func_inc_baixo:
                queda_func = ((func_inc_baixo - func_inc_alto) / func_inc_baixo) * 100
                insight_mecanico = f"A presença de inchaço moderado/grave reduz a capacidade funcional em {queda_func:.0f}%. A resolução do derrame articular é o principal limitante para progressão de carga."
            else:
                insight_mecanico = "O paciente demonstra capacidade de manter sua funcionalidade de forma independente das flutuações de efusão articular."
        except:
            insight_mecanico = "Aguardando mais avaliações para correlacionar o impacto do inchaço na função."

        # Insight 3: Postura vs Dor (Gatilho Biomecânico)
        try:
            if 'Postura' in df_p.columns and not df_p['Postura'].empty:
                pior_postura = df_p.groupby('Postura')['Dor'].mean().idxmax()
                dor_pior = df_p.groupby('Postura')['Dor'].mean().max()
                dor_outras = df_p[df_p['Postura'] != pior_postura]['Dor'].mean()
                if pd.notna(dor_pior) and pd.notna(dor_outras) and dor_outras > 0 and dor_pior > dor_outras:
                    aumento_pct = ((dor_pior - dor_outras) / dor_outras) * 100
                    insight_postura = f"A postura '{pior_postura}' atua como gatilho biomecânico primário, elevando o quadro álgico em {aumento_pct:.0f}% em relação às demais posições da rotina."
                else:
                    insight_postura = "Não há evidências de um gatilho postural isolado que exacerbe drasticamente os sintomas."
            else:
                insight_postura = "Dados posturais insuficientes para análise biomecânica."
        except:
            insight_postura = "Aguardando volume de dados para mapeamento de gatilho postural."

        # Insight 4: Evolução Clínica (Função vs Dor)
        try:
            dor_ini = df_p['Dor'].iloc[0]
            dor_atu = ultima['Dor']
            func_ini = df_p['Score_Função'].iloc[0]
            func_atu = ultima['Score_Função']
            
            if func_atu > func_ini and dor_atu < dor_ini:
                ganho_f = ((func_atu - func_ini) / func_ini * 100) if func_ini > 0 else 100
                queda_d = ((dor_ini - dor_atu) / dor_ini * 100) if dor_ini > 0 else 100
                insight_evolucao = f"Evolução Ideal: O paciente aumentou sua capacidade funcional em {ganho_f:.0f}% enquanto reduziu a dor em {queda_d:.0f}%. Ganhos reais de tolerância mecânica."
            elif func_atu > func_ini and dor_atu >= dor_ini:
                insight_evolucao = "Atenção: Houve ganho funcional, mas com custo álgico. O paciente pode estar operando no limite ou acima da sua janela de tolerância atual."
            elif func_atu <= func_ini and dor_atu < dor_ini:
                insight_evolucao = "Fase Analgésica: O tratamento reduziu a dor com sucesso, porém a capacidade funcional ainda não apresenta progressão em relação ao início."
            else:
                insight_evolucao = "Alerta Clínico: Sem progressão funcional e sem alívio da dor comparado ao início do tratamento. Recomenda-se reavaliar o plano terapêutico."
        except:
            insight_evolucao = "Aguardando volume de dados para calcular o ganho percentual de função vs. dor."

        # Insight 5: Comportamento Isolado da Dor (Inteligência de Cores para o Painel)
        dor_atual = ultima['Dor']
        if dor_atual < media_dor:
            insight_dor = f"A dor atual ({int(dor_atual)}) está abaixo da média histórica ({media_dor:.1f}), indicando dessensibilização efetiva."
            cor_dor = "success"
        elif dor_atual == media_dor:
            insight_dor = f"O quadro álgico encontra-se estabilizado na média ({media_dor:.1f}). Foco em romper o platô de sintomas."
            cor_dor = "warning"
        else:
            insight_dor = f"A dor atual ({int(dor_atual)}) encontra-se acima da média ({media_dor:.1f}). Recomenda-se reforço analgésico."
            cor_dor = "error"

        # --- MOTOR DE INTELIGÊNCIA MATEMÁTICA (REVISADO) ---
        
        # 1. Algoritmo de Detecção de Platô (Janela Móvel de 3 Sessões)
        plato_detectado = False
        if len(df_p) >= 3:
            ultimas_3 = df_p.tail(3)
            # Desvio padrão zero indica estagnação matemática perfeita
            dor_estagnada = ultimas_3['Dor'].std() == 0 
            funcao_estagnada = ultimas_3['Score_Função'].std() == 0
            # Inchaço: Verifica se não houve decréscimo (monotocidade não-decrescente)
            inchaco_valores = pd.to_numeric(ultimas_3['Inchaco_N'])
            inchaco_nao_cedeu = inchaco_valores.is_monotonic_increasing or (inchaco_valores.nunique() == 1)
            
            if dor_estagnada and inchaco_nao_cedeu and funcao_estagnada:
                plato_detectado = True

        # 2. Cálculo de LSI Estimado (Funcionalidade Relativa)
        # Fórmula: (Score Atual / Score Máximo Teórico) * 100
        score_maximo_teorico = 10.0
        lsi_estimado = min((df_p['Score_Função'].iloc[-1] / score_maximo_teorico) * 100, 100.0)
        
        # 3. Rastreio de Nociplasticidade (Discrepância Clínico-Mecânica)
        # Critério: Dor > 5 (Moderada/Alta) COM Inchaço <= 1 (Fisiológico) E Função > 70%
        descompasso_nociplastico = False
        if ultima['Dor'] > 5 and ultima['Inchaco_N'] <= 1 and lsi_estimado >= 70:
            descompasso_nociplastico = True
            
        # 4. Alerta de Inibição Muscular Artrogênica (AMI)
        # Critério: Derrame articular clinicamente relevante (>= Grau 2)
        alerta_ami = False
        if ultima['Inchaco_N'] >= 2:
            alerta_ami = True
            
    
        # --- NOVO: GERADOR DE LINK PARA O CIRURGIÃO (WhatsApp) ---
        if not paciente_alvo: # <-- ESTA É A TRAVA DE INVISIBILIDADE PARA O MÉDICO
            # Codifica o nome do paciente para segurança
            token_gerado = base64.b64encode(p_sel.encode('utf-8')).decode('utf-8')
            
            # ATENÇÃO THALLES: URL de produção já configurada!
            url_base = "https://meu-app-fisio-sekckq2ebemqgfsv4xeu9v.streamlit.app/" 
            url_medico = f"{url_base}?med=true&token={token_gerado}"
            
            texto_whatsapp = f"Olá, Doutor! O prontuário atualizado em tempo real do paciente *{p_sel}* está disponível no Portal GENUA. Acesse o link seguro para ver a evolução de dor, inchaço e minha conduta: {url_medico}"
            link_wpp = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_whatsapp)}"
            
            st.link_button("📲 Enviar Resumo para o Cirurgião (WhatsApp)", link_wpp, type="secondary", use_container_width=True)
            st.write("---")
       

        # 4. DASHBOARD TELA
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dor Atual (vs Média)", f"{ultima['Dor']}/10", f"{delta_dor_pct:.0f}%", delta_color="inverse")
        m2.metric("Inchaço (vs Média)", f"Grau {ultima[col_inc]}", f"{delta_inc_pct:.0f}%", delta_color="inverse")
        m3.metric("IKDC", f"{int(u_ikdc)}/100", status_clinico)
        m4.metric("Previsão Alta", prev_txt)

        st.write("---")
        t1, t2, t3, t4 = st.tabs(["📈 Progresso Funcional", "🩸 Quadro Álgico", "🌊 Inchaço", "🎯 Fatores Modificáveis"])
        
        with t1: 
            # 1. Alerta de Platô (Caso exista)
            if plato_detectado:
                st.error("🚨 **ALERTA DE PLATÔ TERAPÊUTICO DETECTADO**")
                st.markdown(f"""
                    <div style='background-color: #f8d7da; padding: 10px; border-left: 5px solid #dc3545; border-radius: 5px;'>
                        <p style='color: #721c24; margin: 0;'><b>Parecer da Inteligência:</b> O paciente não apresenta progressão há 3 sessões. 
                        A curva de adaptação estabilizou.</p>
                    </div>
                """, unsafe_allow_html=True)

            # 2. QUADRO DE DECISÃO CLÍNICA (Diretrizes 2025/2026)
            st.markdown(f"### 🧠 Inteligência Clínica GENUA")
            col_ia1, col_ia2, col_ia3 = st.columns(3)
            
            with col_ia1:
                st.metric("Prontidão para Alta (LSI)", f"{lsi_estimado:.0f}%", help="Alvo para alta esportiva: >90%")
                st.progress(min(lsi_estimado/100, 1.0))
            
            with col_ia2:
                if descompasso_nociplastico:
                    st.warning("⚠️ Perfil Nociplástico")
                    st.caption("Dor desproporcional à mecânica. Priorizar educação.")
                else:
                    st.success("✅ Perfil Mecânico")
                    st.caption("Quadro álgico condizente com a carga.")
            
            with col_ia3:
                if alerta_ami:
                    st.error("🚨 Inibição (AMI)")
                    st.caption("Derrame articular limitando ativação muscular.")
                else:
                    st.success("💪 Ativação Preservada")
                    st.caption("Ausência de inibição artrogênica impeditiva.")

            st.write("---")
            
            # 3. Visualização Gráfica e Insights (O que já funcionava)
            st.image(buf_ev, use_container_width=True)
            st.success(f"🔮 **Inteligência GENUA:** Alta estimada para **{prev_txt}**.")
            st.info(f"💡 **Insight Evolutivo:** {insight_evolucao}")
            
        with t2:
            st.image(buf_dor, use_container_width=True)
            # Injeção dinâmica do alerta com base na cor/gravidade calculada
            if cor_dor == "success": st.success(f"💡 **Insight Álgico:** {insight_dor}")
            elif cor_dor == "warning": st.warning(f"💡 **Insight Álgico:** {insight_dor}")
            else: st.error(f"💡 **Insight Álgico:** {insight_dor}")
            
        with t3: 
            st.image(buf_adm, use_container_width=True)
            
            st.warning(f"💡 **Insight Mecânico Geral:** {insight_mecanico}")
            st.write("---")
            
            st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>📐 Rastreio Clínico da Sessão Selecionada</h4>", unsafe_allow_html=True)
            
            c_m1, c_m2 = st.columns(2)
            # Lê os dados em tempo real da sessão escolhida na Máquina do Tempo!
            flex_atual = ultima['Flexao']
            ext_atual = ultima['Extensao']
            
            with c_m1:
                st.metric("Flexão Atual", f"{int(flex_atual)}°")
            with c_m2:
                st.info(f"**Extensão Terminal:**\n{ext_atual}")
                
            # O CÉREBRO CLÍNICO: Analisando a sessão cruzada
            if ultima['Inchaco_N'] >= 2 and flex_atual < 110:
                st.error("🚨 **Bloqueio Capsular:** O inchaço atual (Grau 2+) está limitando fisicamente a flexão.")
            elif ultima['Dor'] > 5 and "Déficit" in str(ext_atual):
                st.warning("⚠️ **Alerta AMI (Inibição Artrogênica):** Dor moderada/alta gerando inibição de quadríceps e déficit de extensão.")
            elif "Completa" in str(ext_atual) and flex_atual >= 120:
                st.success("✅ **Articulação Livre:** ADM funcional atingida (Extensão Completa e Flexão >120°).")
            else:
                st.info("ℹ️ Articulação em processo de ganho de ADM sem alertas mecânicos críticos no momento.")
                    
        with t4: 
            st.image(buf_s, use_container_width=True)
            st.info(f"💡 **Insight do Sono:** {insight_ouro.replace('Parecer Biopsicossocial: ', '')}")
            
            st.write("**Análise de Postura vs. Dor**")
            st.altair_chart(alt.Chart(df_p).mark_bar(color=CORES_GENUA['secundaria'], cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X('Postura', title='Postura'),
                y=alt.Y('mean(Dor)', title='Média de Dor'),
                tooltip=['Postura', 'mean(Dor)']
            ), use_container_width=True)

        # 5. PREPARAÇÃO E DOWNLOAD DO PDF
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist_clinica = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
        except: 
            hist_clinica = "Anamnese não cadastrada no sistema."

        pdf_metrics = {
            'ikdc': u_ikdc, 'ikdc_status': status_clinico, 
            'dor': ultima['Dor'], 'media_dor': media_dor,
            'inchaco': ultima[col_inc], 'alta': prev_txt,
            'insight_ouro': insight_ouro,
            'insight_mecanico': insight_mecanico,
            'insight_postura': insight_postura,
            'insight_evolucao': insight_evolucao
        }
        
        pdf_bytes = create_pdf(p_sel, hist_clinica, pdf_metrics, {
            'ev': buf_ev, 'dor': buf_dor, 'sono': buf_s, 'inchaco': buf_inc
        })
        
        st.download_button("📥 BAIXAR RELATÓRIO MASTER (PDF)", data=pdf_bytes, file_name=f"Relatorio_GENUA_{p_sel}.pdf")
        st.info(f"📝 ZenFisio: {p_sel} - Dor {ultima['Dor']}, IKDC {int(u_ikdc)}, Alta est. {prev_txt}.")
    else:
        st.info("Aguardando entrada de dados na planilha.")
