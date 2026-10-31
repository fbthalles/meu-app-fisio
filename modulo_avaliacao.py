"""GENUA | Módulo 1: Avaliação Inicial (O Marco Zero) — Estilo Apple HIG."""
from services.patient_context import preparar_contexto_paciente, payload_do_paciente_ativo, chave_widget
import hashlib
import io
import json
from datetime import datetime
from PIL import Image, ImageDraw
import streamlit as st
import streamlit.components.v1 as components

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fpdf import FPDF

try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    _HAS_IMAGE_COORDS = True
except (ImportError, Exception):
    _HAS_IMAGE_COORDS = False

from config import CORES_GENUA, titulo, secao, toast
from firebase_client import db, invalidar_cache


# ============================================================
# 1. RESILIÊNCIA MOBILE (WAKE LOCK API) & HELPERS DE DATA/PARSING
# ============================================================
def _injetar_wake_lock_avaliacao():
    """Impede que a tela do celular apague durante a avaliação e mantém o WebSocket ativo."""
    components.html(
        """
        <script>
        (function() {
            async function ativarWakeLock() {
                try {
                    if ('wakeLock' in navigator) {
                        await navigator.wakeLock.request('screen');
                    }
                } catch (e) {}
            }
            ativarWakeLock();
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible') ativarWakeLock();
            });
            setInterval(() => {
                if (document.visibilityState === 'visible') {
                    window.dispatchEvent(new Event('resize'));
                }
            }, 25000);
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def _parse_data_br(data_str: str) -> datetime:
    """Converte string de data (DD/MM/YYYY ou YYYY-MM-DD) em datetime seguro para ordenação."""
    if not data_str:
        return datetime(2000, 1, 1)
    s = str(data_str).strip()[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return datetime(2000, 1, 1)


def _detectar_proms_legados(dados: dict) -> list:
    """Infere quais questionários foram preenchidos em avaliações salvas."""
    if not dados:
        return []
    if isinstance(dados.get("PROMs_Aplicados"), list):
        return dados["PROMs_Aplicados"]

    aplicados = []
    if float(dados.get("LEFS_Pct", 0) or 0) > 0:
        aplicados.append("LEFS")
    visap = float(dados.get("VISA_P_Pts", 0) or 0)
    if visap > 0 and visap != 50.0:
        aplicados.append("VISA-P")
    lysh = float(dados.get("Lysholm_Pts", 0) or 0)
    if lysh > 0 and lysh != 100.0:
        aplicados.append("Lysholm")
    womac = float(dados.get("WOMAC_Pct", 0) or 0)
    if womac > 0 and round(womac, 1) != 100.0:
        aplicados.append("WOMAC")
    koos = float(dados.get("KOOS_Pct", 0) or 0)
    if koos > 0 and round(koos, 1) != 100.0:
        aplicados.append("KOOS")
    ikdc = float(dados.get("IKDC_Pct", 0) or 0)
    if ikdc > 0 and round(ikdc, 1) != 75.0:
        aplicados.append("IKDC")
    return aplicados


def _limpar_latin1(texto) -> str:
    """Sanitiza strings para o motor FPDF2 (latin-1)."""
    if texto is None:
        return "-"
    s = (
        str(texto)
        .replace("≥", ">=")
        .replace("≤", "<=")
        .replace("—", "-")
        .replace("–", "-")
        .replace("•", "*")
        .replace("🟢", "[OK] ")
        .replace("🟡", "[ATENCAO] ")
        .replace("🔴", "[ALERTA] ")
        .replace("🚨", "[CRITICO] ")
        .replace("⭐", "[EXCELENTE] ")
    )
    return s.encode("latin-1", "replace").decode("latin-1")


# ============================================================
# 2. GERADOR DE PDF EXCLUSIVO DA AVALIAÇÃO INICIAL (FPDF2 + MATPLOTLIB)
# ============================================================
class PDFSomenteAvaliacao(FPDF):
    def header(self):
        # Barra institucional GENUA (#103E55 e #2E8B9A)
        self.set_fill_color(16, 62, 85)
        self.rect(0, 0, 140, 5, "F")
        self.set_fill_color(46, 139, 154)
        self.rect(140, 0, 70, 5, "F")
        self.set_y(10)

    def footer(self):
        self.set_y(-14)
        self.set_font("Arial", "I", 7.5)
        self.set_text_color(100, 116, 139)
        self.cell(
            0,
            10,
            _limpar_texto_pdf(f"GENUA Instituto de Fisioterapia Esportiva | Laudo Exclusivo de Avaliacao Inicial | Pagina {self.page_no()}/{{nb}}"),
            0,
            0,
            "C",
        )


def _limpar_texto_pdf(txt):
    return _limpar_latin1(txt)


def gerar_pdf_somente_avaliacao(dados_av: dict) -> bytes:
    """
    Gera um arquivo PDF (.pdf) contendo EXCLUSIVAMENTE a Avaliação Inicial:
    Cabeçalho GENUA, Anamnese & Objetivo, Exame Físico & Perimetria Segmentada,
    Métricas de Simetria (LSI + Razão I:Q), Gráfico de Força e Resumo da Conduta.
    """
    pdf = PDFSomenteAvaliacao()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # Banner Principal
    pdf.set_fill_color(16, 62, 85)
    pdf.rect(10, 10, 190, 22, "F")
    pdf.set_xy(14, 13)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(255, 255, 255)
    pac_nome = _limpar_latin1(dados_av.get("Paciente", "Paciente"))
    pdf.cell(0, 7, f"GENUA | LAUDO DE AVALIACAO CLINICA INICIAL", 0, 1, "L")
    pdf.set_x(14)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(165, 243, 252)
    pdf.cell(
        0,
        6,
        _limpar_latin1(
            f"Paciente: {pac_nome}   |   Data: {dados_av.get('Data_Avaliacao', '-')}   |   Lado Acometido: {dados_av.get('Lado_Acometido', '-')}   |   Fenotipo: {dados_av.get('Fenotipo_Clinico', 'Geral')}"
        ),
        0,
        1,
        "L",
    )

    pdf.set_y(36)

    def bloco_titulo(titulo_sec: str):
        pdf.ln(2)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(16, 62, 85)
        pdf.set_font("Arial", "B", 9.5)
        pdf.cell(0, 7, _limpar_latin1(f"  {titulo_sec.upper()}"), 0, 1, "L", fill=True)
        pdf.ln(1.5)

    def linha_campo(rotulo: str, valor: str):
        pdf.set_font("Arial", "B", 8.5)
        pdf.set_text_color(30, 41, 59)
        pdf.write(4.8, _limpar_latin1(f"{rotulo}: "))
        pdf.set_font("Arial", "", 8.5)
        pdf.set_text_color(51, 65, 85)
        pdf.write(4.8, _limpar_latin1(f"{valor}\n"))

    # 1. ANAMNESE, OBJETIVO FUNCIONAL E BANDEIRAS
    bloco_titulo("1. Anamnese, Objetivo Funcional e Triagem Biopsicossocial")
    linha_campo("Queixa Principal (QP)", dados_av.get("QP", "-"))
    linha_campo("Historia da Molestia Atual (HMA)", dados_av.get("HMA", "-"))
    linha_campo(
        "Objetivo Funcional do Paciente",
        f"{dados_av.get('Objetivo_Paciente', '-')} (SANE Baseline: {dados_av.get('SANE_Baseline_Pct', 0)}%)",
    )
    linha_campo(
        "Comportamento da Dor",
        f"{dados_av.get('Class_Dor', '-')} | Origem: {dados_av.get('Origem_Dor', '-')} | Zonas: {dados_av.get('Zonas_Dor', '-')}",
    )
    linha_campo(
        "Alivio / Piora",
        f"Alivio: {dados_av.get('Fatores_Alivio', '-')}  |  Piora: {dados_av.get('Fatores_Piora', '-')}",
    )
    linha_campo(
        "Bandeiras e Comorbidades",
        f"Red: {dados_av.get('Red_Flags', 'Nenhuma')} | Yellow: {dados_av.get('Yellow_Cog', 'Nenhum')} | Blue: {dados_av.get('Fatores_Sociais', 'Nenhum')} | Comorbidades: {dados_av.get('Comorbidades', 'Nenhuma')}",
    )

    # 2. EXAME FÍSICO, HIPOTROFISMO E PERIMETRIA SEGMENTADA
    bloco_titulo("2. Exame Fisico, Hipotrofismo e Perimetria (Coxa e Perna)")
    linha_campo("Marcha e Derrame", f"Marcha: {dados_av.get('Marcha', '-')} | Derrame: {dados_av.get('Derrame', '-')}")
    linha_campo("Hipotrofismo Muscular (Dir)", dados_av.get("Hipotrofismo_Detalhado_Dir", dados_av.get("Trofismo_Dir", "Normal")))
    linha_campo("Hipotrofismo Muscular (Esq)", dados_av.get("Hipotrofismo_Detalhado_Esq", dados_av.get("Trofismo_Esq", "Normal")))
    linha_campo("Perimetria Coxa (+5/+10/+15/+20 cm)", dados_av.get("Perimetria_Coxa_Resumo", dados_av.get("Perimetria", "-")))
    linha_campo("Perimetria Panturrilha (-5/-10/-15 cm)", dados_av.get("Perimetria_Perna_Resumo", "-"))
    linha_campo("Estruturas Dolorosas a Palpacao", dados_av.get("Palpacao", "-"))
    linha_campo(
        "Testes Ortopedicos (+)",
        f"Ligamentares: {dados_av.get('Testes_Ligamentares', '-')} | Meniscais: {dados_av.get('Testes_Meniscais', '-')} | Femoropatelares/Compressao: {dados_av.get('Testes_Femoropatelar', '-')}",
    )
    linha_campo(
        "Mobilidade (ADM) e Flexibilidade",
        f"Flexao: {dados_av.get('ADM_Joelho_Flexao', '-')} | Extensao: {dados_av.get('ADM_Joelho_Extensao', '-')} | Lunge: {dados_av.get('Lunge_Test', '-')} | Flexibilidade: {dados_av.get('Flexibilidade', '-')}",
    )

    # 3. FORÇA MUSCULAR, SIMETRIA (LSI), RAZÃO I:Q E GRÁFICO
    bloco_titulo("3. Avaliacao de Forca, Simetria (LSI) e Equilibrio Muscular (Razao I:Q)")
    modo_forca = dados_av.get("Modo_Avaliacao_Forca", "Dinamometria Isométrica (kgf)")
    linha_campo("Modalidade de Avaliacao de Forca", modo_forca)

    if "Não Aplicável" in modo_forca or "Pós-Op" in modo_forca:
        linha_campo(
            "Nota Clinica de Protecao Tecidual",
            "Avaliacao de forca maxima omitida nesta fase (Pos-Operatorio / Protecao Biologica do Enxerto ou Sutura).",
        )
    elif "Oxford" in modo_forca:
        linha_campo("Escala Manual de Oxford (0-5)", f"Direito: {dados_av.get('Forca_Geral_Dir', '-')}  |  Esquerdo: {dados_av.get('Forca_Geral_Esq', '-')}")
    else:
        linha_campo("Dinamometria Isométrica (kgf)", f"Direito: {dados_av.get('Dinamometria_Dir', '-')}  |  Esquerdo: {dados_av.get('Dinamometria_Esq', '-')}")
        linha_campo("Indices de Simetria (LSI) & Razao I:Q", dados_av.get("Resumo_LSI_IQ", "-"))

        # Gera gráfico comparativo de força se houver dinamometria > 0
        din_map = dados_av.get("Dinamometria_Dict", {})
        if isinstance(din_map, dict) and any(float(v or 0) > 0 for v in din_map.values()):
            fig, ax = plt.subplots(figsize=(6.2, 2.3), dpi=150)
            grupos = ["Quadríceps", "Isquiotibiais", "Abdutores", "Adutores"]
            vals_d = [
                float(din_map.get("ext_d", 0)),
                float(din_map.get("flex_d", 0)),
                float(din_map.get("abd_d", 0)),
                float(din_map.get("add_d", 0)),
            ]
            vals_e = [
                float(din_map.get("ext_e", 0)),
                float(din_map.get("flex_e", 0)),
                float(din_map.get("abd_e", 0)),
                float(din_map.get("add_e", 0)),
            ]
            x = range(len(grupos))
            w = 0.35
            b1 = ax.bar([i - w / 2 for i in x], vals_d, width=w, label="Direito (kgf)", color="#103E55")
            b2 = ax.bar([i + w / 2 for i in x], vals_e, width=w, label="Esquerdo (kgf)", color="#2E8B9A")
            ax.set_xticks(list(x))
            ax.set_xticklabels(grupos, fontsize=8, fontweight="bold")
            ax.set_ylabel("kgf", fontsize=8)
            ax.set_title("Dinamometria Isometrica Bilateral (kgf)", fontsize=9, fontweight="bold", color="#103E55")
            ax.legend(fontsize=7.5, frameon=False)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            for rect in list(b1) + list(b2):
                h = rect.get_height()
                if h > 0:
                    ax.annotate(f"{h:.1f}", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 2), textcoords="offset points", ha="center", fontsize=7, fontweight="bold")
            fig.tight_layout()
            img_buf = io.BytesIO()
            fig.savefig(img_buf, format="png", dpi=150)
            plt.close(fig)
            img_buf.seek(0)
            pdf.ln(1)
            pdf.image(img_buf, x=22, w=165)
            pdf.ln(2)

    # 4. CONTROLE MOTOR, QUESTIONÁRIOS E CONDUTA
    bloco_titulo("4. Controle Motor, Questionarios (PROMs) e Conduta Terapeutica")
    linha_campo("Controle Motor / Relacao Funcional com Dor", dados_av.get("Resumo_Controle_Motor", "Opcional / Nao aplicado"))
    proms_ap = dados_av.get("PROMs_Aplicados", [])
    if proms_ap:
        resumo_p = []
        if "KOOS" in proms_ap:
            resumo_p.append(f"KOOS: {dados_av.get('KOOS_Pct', 0):.1f}%")
        if "IKDC" in proms_ap:
            resumo_p.append(f"IKDC: {dados_av.get('IKDC_Pct', 0):.1f}%")
        if "LEFS" in proms_ap:
            resumo_p.append(f"LEFS: {dados_av.get('LEFS_Pct', 0):.1f}%")
        if "Lysholm" in proms_ap:
            resumo_p.append(f"Lysholm: {dados_av.get('Lysholm_Pts', 0)} pts")
        if "VISA-P" in proms_ap:
            resumo_p.append(f"VISA-P: {dados_av.get('VISA_P_Pts', 0)} pts")
        if "WOMAC" in proms_ap:
            resumo_p.append(f"WOMAC: {dados_av.get('WOMAC_Pct', 0):.1f}%")
        linha_campo("Questionarios Validados Aplicados", " | ".join(resumo_p))
    linha_campo("Exames Complementares", f"{dados_av.get('Exames_Apresentados', 'Nenhum')} — {dados_av.get('Laudo_Exames', '-')}")
    linha_campo("Resumo da Conduta Clinica / Planejamento", dados_av.get("Conduta_Avaliacao", "Reabilitacao baseada no fenotipo clinico e controle gradual de carga."))

    saida = pdf.output(dest="S")
    if isinstance(saida, str):
        return saida.encode("latin-1", "replace")
    return bytes(saida)


# ============================================================
# 3. MONITOR DE AUTO-SAVE A CADA 5 SEGUNDOS (BACKGROUND FRAGMENT)
# ============================================================
@st.fragment(run_every="5s")
def _fragmento_autosave_avaliacao():
    """
    Salva automaticamente a avaliação em andamento a cada 5 segundos no Firestore
    sem precisar clicar no botão de salvar e sem recarregar a página.
    """
    payload = st.session_state.get("_payload_avaliacao_atual")
    if not payload or not isinstance(payload, dict):
        return
    if not payload_do_paciente_ativo(payload, st.session_state):
        st.caption("⚠️ Salvamento bloqueado: o registro não pertence ao paciente ativo.")
        return

    qp_atual = str(payload.get("QP", "")).strip()
    paciente_atual = str(payload.get("Paciente", "")).strip()
    if not paciente_atual or not qp_atual:
        st.caption("🟡 *Auto-save ativo (preencha a Queixa Principal na aba Anamnese para iniciar a gravação automática na nuvem).*")
        return

    serializado = json.dumps(payload, sort_keys=True, default=str)
    hash_atual = hashlib.md5(serializado.encode("utf-8")).hexdigest()
    ultimo_hash = st.session_state.get("_ultimo_hash_autosave", "")

    if hash_atual != ultimo_hash:
        try:
            doc_id = st.session_state.get("doc_id_avaliacao")
            if doc_id:
                db.collection("Avaliacao_Inicial").document(doc_id).set(payload, merge=True)
            else:
                _, doc_ref = db.collection("Avaliacao_Inicial").add(payload)
                st.session_state.doc_id_avaliacao = doc_ref.id
            invalidar_cache("Avaliacao_Inicial")
            st.session_state["_ultimo_hash_autosave"] = hash_atual
            st.session_state["_horario_ultimo_autosave"] = datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            st.caption(f"⚠️ Reconectando auto-save: {str(e)[:40]}")

    hora_salvo = st.session_state.get("_horario_ultimo_autosave")
    if hora_salvo:
        st.caption(f"🟢 **Salvo automaticamente na nuvem às {hora_salvo}** *(verificação contínua a cada 5s)*")


# ============================================================
# 4. FUNÇÃO PRINCIPAL DE RENDERIZAÇÃO DA TELA
# ============================================================
def render():
    preparar_contexto_paciente(st.session_state)
    _injetar_wake_lock_avaliacao()

    # Cabeçalho limpo estilo Apple Health
    st.markdown(f"""
        <div style='margin-bottom: 14px;'>
            <h2 style='margin-bottom: 4px;'>🔎 Avaliação Inicial (Marco Zero)</h2>
            <p style='color: {CORES_GENUA['texto_suave']}; font-size: 0.94rem; margin: 0;'>
                Primeira Consulta · Baseline Bilateral, Fenótipo Clínico, Perimetria Padronizada, Força (LSI + Razão I:Q), SANE e PROMs.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --- MOTOR DE CONSULTA E EDIÇÃO ---
    st.session_state.setdefault("doc_id_avaliacao", None)
    st.session_state.setdefault("dados_antigos", None)

    avaliacoes_existentes = []
    if "paciente" in st.session_state and st.session_state.paciente:
        try:
            docs = db.collection("Avaliacao_Inicial").where("Paciente", "==", st.session_state.paciente).stream()
            avaliacoes_existentes = [{"id": d.id, "data": d.to_dict()} for d in docs]
            avaliacoes_existentes.sort(
                key=lambda x: _parse_data_br(x["data"].get("Data_Avaliacao", "01/01/2000")),
                reverse=True,
            )
        except Exception:
            avaliacoes_existentes = []

    # CARD SELETOR DE MODO (Nova Avaliação x Editar Existente)
    with st.container(border=True):
        col_modo1, col_modo2 = st.columns([2.5, 1])
        with col_modo1:
            if avaliacoes_existentes:
                opcoes = ["➕ Nova Avaliação"] + [
                    f"✏️ Editar ({a['data'].get('Data_Avaliacao', '?')}) — QP: {a['data'].get('QP', 'Sem descrição')[:45]}"
                    for a in avaliacoes_existentes
                ]
                escolha = st.selectbox(
                    "🎯 Modo de Operação:",
                    opcoes,
                    key="seletor_avaliacao",
                    help="Selecione 'Nova Avaliação' para criar do zero ou escolha uma existente para editar.",
                )
            else:
                st.info("ℹ️ Este paciente ainda não possui Avaliação Inicial. Preencha os campos abaixo (salvamento automático a cada 5s).")
                escolha = "➕ Nova Avaliação"

        with col_modo2:
            if avaliacoes_existentes and escolha != "➕ Nova Avaliação":
                st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Excluir Avaliação", type="secondary", width="stretch"):
                    st.session_state["confirmar_exclusao_aval"] = True

        if st.session_state.get("confirmar_exclusao_aval"):
            st.warning("⚠️ Tem certeza? Esta ação removerá a avaliação permanentemente.")
            cc1, cc2, _ = st.columns([1, 1, 2])
            with cc1:
                if st.button("✅ Sim, excluir", type="primary", width="stretch"):
                    try:
                        idx = opcoes.index(escolha) - 1
                        doc_id = avaliacoes_existentes[idx]["id"]
                        db.collection("Avaliacao_Inicial").document(doc_id).delete()
                        invalidar_cache("Avaliacao_Inicial")
                        st.session_state["confirmar_exclusao_aval"] = False
                        st.session_state.doc_id_avaliacao = None
                        toast("Avaliação excluída com sucesso.", "success")
                        st.rerun()
                    except Exception as e:
                        toast(f"Erro ao excluir: {e}", "error")
            with cc2:
                if st.button("❌ Cancelar", type="secondary", width="stretch"):
                    st.session_state["confirmar_exclusao_aval"] = False
                    st.rerun()

    if escolha == "➕ Nova Avaliação":
        if st.session_state.get("_ultima_escolha_aval") != "➕ Nova Avaliação":
            st.session_state.doc_id_avaliacao = None
            st.session_state.dados_antigos = None
        st.session_state["_ultima_escolha_aval"] = "➕ Nova Avaliação"
    else:
        idx = opcoes.index(escolha) - 1
        st.session_state.dados_antigos = avaliacoes_existentes[idx]["data"]
        st.session_state.doc_id_avaliacao = avaliacoes_existentes[idx]["id"]
        st.session_state["_ultima_escolha_aval"] = escolha

    dados = st.session_state.get("dados_antigos") or {}
    modo_edicao = st.session_state.get("doc_id_avaliacao") is not None

    def get_idx(opcoes_lista, chave, fallback_chave=None):
        val = dados.get(chave)
        if val is None and fallback_chave:
            val = dados.get(fallback_chave)
        return opcoes_lista.index(val) if val in opcoes_lista else 0

    def get_list(*args):
        chave = args[-1]
        opcoes_lista = args[0] if len(args) > 1 else None
        val = dados.get(chave, [])
        if not val or val in ["Nenhuma", "Nenhum", "Normal", "Sem dor", "Não testado"]:
            return []
        lista_bruta = val if isinstance(val, list) else [v.strip() for v in str(val).split(",")]
        lista_corrigida = []
        for v in lista_bruta:
            if v == "Difusa/Articular":
                v = "Difusa"
            if v == "Nenhum" and opcoes_lista and "Nenhuma" in opcoes_lista:
                v = "Nenhuma"
            if v == "Nenhuma" and opcoes_lista and "Nenhum" in opcoes_lista:
                v = "Nenhum"
            lista_corrigida.append(v)
        if opcoes_lista:
            return [v for v in lista_corrigida if v in opcoes_lista]
        return [v for v in lista_corrigida if v not in ["Nenhuma", "Nenhum", "Normal", "Sem dor", "Não testado"]]

    doc_atual_key = st.session_state.get("doc_id_avaliacao") or "nova"
    if st.session_state.get("_ultimo_doc_mapa") != doc_atual_key:
        pontos_salvos = dados.get("Pontos_Mapa_Dor", [])
        st.session_state.pontos_dor = pontos_salvos if isinstance(pontos_salvos, list) else []
        st.session_state.last_click = None
        st.session_state["_ultimo_doc_mapa"] = doc_atual_key

    # ============================================================
    # NAVEGAÇÃO EM ABAS
    # ============================================================
    t_anamnese, t_dor, t_flags, t_fisico, t_funcional, t_exames, t_quest = st.tabs([
        "🗣️ Anamnese & Objetivo", "💥 Dor", "🚩 Bandeiras", "📐 Físico & Perimetria", "🏃 Funcional & Força", "🩻 Exames", "📋 Questionários"
    ])

    # ------------------------------------------------------------
    # ABA 1: ANAMNESE + OBJETIVO FUNCIONAL DO PACIENTE (SANE)
    # ------------------------------------------------------------
    with t_anamnese:
        with st.container(border=True):
            secao(
                "🗣️ Histórico Clínico, Fenótipo e Lateralidade",
                "Mapeamento do membro acometido, fenótipo clínico (para parametrizar Pós-Op vs Reabilitação Funcional), queixa principal e HMA."
            )
            c_qp, c_lado, c_data_av = st.columns([2.0, 1.1, 0.9])
            with c_qp:
                qp = st.text_input(
                    "Queixa Principal (QP) *",
                    value=dados.get("QP", ""),
                    placeholder="O que o paciente deixou de fazer devido à dor?",
                    key=chave_widget(st.session_state, 'avaliacao:qp'),
                )
            with c_lado:
                op_lado = ["Direito", "Esquerdo", "Bilateral (Dir > Esq)", "Bilateral (Esq > Dir)", "Bilateral (Simétrico)"]
                lado_acometido = st.selectbox(
                    "🦵 Lado Acometido Principal *",
                    op_lado,
                    index=get_idx(op_lado, "Lado_Acometido"),
                    key=chave_widget(st.session_state, 'avaliacao:lado_acometido'),
                )
            with c_data_av:
                dt_av_default = _parse_data_br(dados.get("Data_Avaliacao")) if modo_edicao and dados.get("Data_Avaliacao") else datetime.now()
                data_aval_input = st.date_input(
                    "📅 Data da Avaliação",
                    value=dt_av_default,
                    format="DD/MM/YYYY",
                    key=chave_widget(st.session_state, 'avaliacao:data_aval_input'),
                )
            op_fenotipo = [
                "Pós-Operatório Agudo / Proteção Tecidual",
                "Pós-Operatório Intermediário / Remodelamento",
                "Déficit de Força / Sobrecarga Mecânica (Tendinopatia / SFP)",
                "Déficit de Controle Motor / Instabilidade Funcional",
                "Dor Persistente / Sensibilização Central",
                "Osteoartrose / Degenerativo",
            ]
            fenotipo_clinico = st.selectbox(
                "🧬 Fenótipo Clínico Predominante (Parametriza Força e Controle Motor)",
                op_fenotipo,
                index=get_idx(op_fenotipo, "Fenotipo_Clinico"),
                help="Em casos de Pós-Operatório Agudo, a dinamometria máxima e testes de corrida/salto tornam-se opcionais automaticamente.",
                key=chave_widget(st.session_state, 'avaliacao:fenotipo_clinico'),
            )
            hma = st.text_area(
                "História da Moléstia Atual (HMA) *",
                value=dados.get("HMA", ""),
                placeholder="Descrição detalhada do mecanismo de lesão, data da cirurgia (se Pós-Op), início e evolução do quadro...",
                height=100,
                key=chave_widget(st.session_state, 'avaliacao:hma'),
            )
            sinais_sintomas = st.text_input(
                "Sinais e Sintomas Associados",
                value=dados.get("Sinais_Sintomas", ""),
                placeholder="Ex: Dor na interlinha medial, crepitação, falseio, bloqueio...",
                key=chave_widget(st.session_state, 'avaliacao:sinais_sintomas'),
            )
            c_an1, c_an2 = st.columns(2)
            with c_an1:
                fat_alivio = st.text_input("🟢 Fatores de Alívio", value=dados.get("Fatores_Alivio", ""), placeholder="Ex: Repouso, crioterapia, extensão ativa...", key=chave_widget(st.session_state, 'avaliacao:fat_alivio'))
            with c_an2:
                fat_piora = st.text_input("🔴 Fatores de Piora", value=dados.get("Fatores_Piora", ""), placeholder="Ex: Descer escadas, agachamento profundo, corrida...", key=chave_widget(st.session_state, 'avaliacao:fat_piora'))

            trat_previos = st.text_area(
                "Tratamentos e Intervenções Anteriores",
                value=dados.get("Tratamentos_Previos", ""),
                placeholder="Cirurgias prévias, infiltrações, fisioterapia anterior...",
                height=75,
                key=chave_widget(st.session_state, 'avaliacao:trat_previos'),
            )
        # Card de Objetivo Funcional do Paciente na Aba Anamnese (SANE mantido, PSFS removido)
        with st.container(border=True):
            secao(
                "🎯 Objetivo Funcional do Paciente & Capacidade Atual (SANE)",
                "Desfecho centrado no paciente: defina a meta principal e o percentual de capacidade percebida hoje (SANE 0% a 100%)."
            )
            obj_val_antigo = dados.get("Objetivo_Paciente", "")
            if obj_val_antigo == "Não relatado":
                obj_val_antigo = ""

            c_obj1, c_obj2 = st.columns([1.8, 1.2], gap="large")
            with c_obj1:
                obj_paciente = st.text_input(
                    "🏆 Qual é o principal objetivo funcional do paciente?",
                    value=obj_val_antigo,
                    placeholder="Ex: Voltar a correr 10 km sem dor, jogar futebol, agachar e brincar com os filhos...",
                    key=chave_widget(st.session_state, 'avaliacao:obj_paciente'),
                )
            with c_obj2:
                sane_baseline = st.slider(
                    "📏 Capacidade Percebida Hoje (SANE: 0% a 100%)",
                    min_value=0,
                    max_value=100,
                    step=5,
                    value=int(dados.get("SANE_Baseline_Pct", 30) if dados.get("SANE_Baseline_Pct") is not None else 30),
                    help="0% = Incapaz / Ponto zero | 100% = Plenamente recuperado.",
                    key=chave_widget(st.session_state, 'avaliacao:sane_baseline'),
                )
            conduta_avaliacao = st.text_area(
                "🧭 Resumo da Conduta Inicial / Planejamento Terapêutico (Sairá no Laudo PDF da Avaliação)",
                value=dados.get("Conduta_Avaliacao", ""),
                placeholder="Ex: Fase 1 focada em controle de efusão articular, ganho de extensão terminal 0° e ativação isométrica de quadríceps...",
                height=75,
                key=chave_widget(st.session_state, 'avaliacao:conduta_avaliacao'),
            )
    # ------------------------------------------------------------
    # ABA 2: DOR E MAPA ANATÔMICO
    # ------------------------------------------------------------
    with t_dor:
        with st.container(border=True):
            secao("💥 Classificação Neurofisiológica e Origem", "Defina o mecanismo predominante de dor (IASP) e o início dos sintomas.")
            c_dor1, c_dor2 = st.columns(2)
            op_class = [
                "Nociceptiva (Mecânica/Inflamatória)",
                "Neuropática (Irradiação/Queimação)",
                "Nociplástica (Sensibilização Central)",
                "Não Aplicável",
            ]
            with c_dor1:
                class_dor = st.selectbox("Classificação da Dor *", op_class, index=get_idx(op_class, "Class_Dor"), key=chave_widget(st.session_state, 'avaliacao:class_dor'))

            op_origem = ["Traumática", "Insidiosa / Sobrecarga", "Pós-operatória", "Degenerativa", "Não Aplicável"]
            with c_dor2:
                origem_dor = st.selectbox("Origem / Mecanismo *", op_origem, index=get_idx(op_origem, "Origem_Dor"), key=chave_widget(st.session_state, 'avaliacao:origem_dor'))

        with st.container(border=True):
            secao("🎯 Mapa Anatômico Interativo da Dor", "Toque ou clique diretamente sobre a imagem do joelho para registrar os pontos álgicos.")

            if "pontos_dor" not in st.session_state:
                st.session_state.pontos_dor = []
            if "last_click" not in st.session_state:
                st.session_state.last_click = None
            if "map_key" not in st.session_state:
                st.session_state.map_key = 0

            c_mapa1, c_mapa2 = st.columns([1.2, 1.8], gap="large")
            with c_mapa1:
                try:
                    img_base = Image.open("mapa_joelho.png").convert("RGB")
                    img_base.thumbnail((350, 600))
                    draw = ImageDraw.Draw(img_base)

                    for ponto in st.session_state.pontos_dor:
                        if isinstance(ponto, dict):
                            px, py = ponto.get("x", 0), ponto.get("y", 0)
                        elif isinstance(ponto, (tuple, list)) and len(ponto) >= 2:
                            px, py = ponto[0], ponto[1]
                        else:
                            continue
                        raio = 7
                        draw.ellipse((px - raio, py - raio, px + raio, py + raio), fill="#FF3B30", outline="#FFFFFF", width=2)

                    if _HAS_IMAGE_COORDS:
                        value = streamlit_image_coordinates(img_base, key=f"joelho_map_{st.session_state.map_key}")
                    else:
                        st.image(img_base, caption="Mapa de Dor")
                        value = None

                    if value is not None:
                        current_click = {"x": value["x"], "y": value["y"]}
                        if st.session_state.last_click != current_click:
                            st.session_state.pontos_dor.append(current_click)
                            st.session_state.last_click = current_click
                            st.session_state.map_key += 1
                            st.rerun()
                except FileNotFoundError:
                    st.warning("⚠️ Arquivo 'mapa_joelho.png' não encontrado na raiz do projeto.")
                except Exception as e:
                    st.warning(f"⚠️ Não foi possível renderizar o mapa interativo: {e}")

            with c_mapa2:
                op_zonas = [
                    "Anterior (Patelar)", "Anterior (Tendão)", "Medial (Interlinha)",
                    "Lateral (Interlinha)", "Posterior (Poplítea)", "Difusa", "Nenhuma"
                ]
                c_z1, c_z2 = st.columns(2)
                with c_z1:
                    zonas_dor_d = st.multiselect(
                        "📍 Zonas de Dor — Joelho DIREITO",
                        op_zonas,
                        default=get_list(op_zonas, "Zonas_Dor_Dir") or (get_list(op_zonas, "Zonas_Dor") if "Direito" in lado_acometido or "Bilateral" in lado_acometido else []),
                        key=chave_widget(st.session_state, 'avaliacao:zonas_dor_d'),
                    )
                with c_z2:
                    zonas_dor_e = st.multiselect(
                        "📍 Zonas de Dor — Joelho ESQUERDO",
                        op_zonas,
                        default=get_list(op_zonas, "Zonas_Dor_Esq") or (get_list(op_zonas, "Zonas_Dor") if "Esquerdo" in lado_acometido or "Bilateral" in lado_acometido else []),
                        key=chave_widget(st.session_state, 'avaliacao:zonas_dor_e'),
                    )
                mapa_dor = st.text_area(
                    "📝 Notas Detalhadas do Mapa da Dor",
                    value=dados.get("Mapa_Dor", ""),
                    placeholder="Ex: Dor puntiforme no polo inferior da patela direita ao agachar...",
                    height=115,
                    key=chave_widget(st.session_state, 'avaliacao:mapa_dor'),
                )
                if st.button("🗑️ Limpar Marcadores do Mapa", type="secondary"):
                    st.session_state.pontos_dor = []
                    st.session_state.last_click = None
                    st.session_state.map_key += 1
                    st.rerun()

    # ------------------------------------------------------------
    # ABA 3: BANDEIRAS E COMORBIDADES (ATUALIZADAS)
    # ------------------------------------------------------------
    with t_flags:
        with st.container(border=True):
            secao(
                "🚩 Sistema de Triagem por Bandeiras e Comorbidades (PBE)",
                "Rastreio de sinais de alerta clínico (Red Flags), moduladores psicossociais (Yellow/Blue Flags) e comorbidades."
            )

            op_red = [
                "Nenhuma", "Histórico de Câncer", "Perda de peso inexplicada",
                "Febre/Calafrios (Infecção)", "Sinais de TVP (Calor/Edema panturrilha)",
                "Déficit Neurológico Progressivo", "Trauma Agudo com deformidade",
                "Incapacidade total de descarga de peso"
            ]
            red_flags = st.multiselect(
                "🚨 Red Flags (Sinais de Alerta Estrutural/Sistêmico) *",
                op_red,
                default=get_list(op_red, "Red_Flags"),
                key=chave_widget(st.session_state, 'avaliacao:red_flags'),
            )
            op_yellow = [
                "Nenhum", "Cinesiofobia (Medo de movimento)", "Catastrofização",
                "Baixa auto-eficácia", "Sintomas depressivos / Ansiedade",
                "Expectativas irreais de recuperação"
            ]
            yellow_cog = st.multiselect(
                "🟡 Yellow Flags (Fatores Cognitivo-Emocionais) *",
                op_yellow,
                default=get_list(op_yellow, "Yellow_Cog"),
                key=chave_widget(st.session_state, 'avaliacao:yellow_cog'),
            )
            c_fl1, c_fl2 = st.columns(2)
            op_sono = ["Normal/Restaurador", "Irregular", "Ruim (Insônia/Acorda com dor)"]
            with c_fl1:
                qualidade_sono = st.selectbox("🌙 Qualidade do Sono *", op_sono, index=get_idx(op_sono, "Sono"), key=chave_widget(st.session_state, 'avaliacao:qualidade_sono'))

            # Blue Flags: Retirado Litígio | Adicionados Problemas familiares, Movimentos Repetitivos, Longos períodos em posição mantida
            op_sociais = [
                "Nenhum",
                "Problemas familiares",
                "Movimentos Repetitivos",
                "Longos períodos em posição mantida",
                "Trabalho braçal/Carga pesada",
                "Afastado pelo INSS",
                "Falta de suporte familiar",
            ]
            with c_fl2:
                fat_sociais = st.multiselect(
                    "🔵 Blue Flags (Fatores Ocupacionais e Contextuais) *",
                    op_sociais,
                    default=get_list(op_sociais, "Fatores_Sociais"),
                    key=chave_widget(st.session_state, 'avaliacao:fat_sociais'),
                )
            # Comorbidades: Adicionado Sedentarismo
            op_comorb = [
                "Nenhuma",
                "Sedentarismo",
                "Hipertensão",
                "Diabetes",
                "Obesidade (IMC > 30)",
                "Cardiopatia",
                "Doença Autoimune",
                "Osteoporose",
                "Tabagismo",
                "Distúrbio Vascular",
            ]
            comorbidades = st.multiselect(
                "🩺 Comorbidades Associadas *",
                op_comorb,
                default=get_list(op_comorb, "Comorbidades"),
                key=chave_widget(st.session_state, 'avaliacao:comorbidades'),
            )
    # ------------------------------------------------------------
    # ABA 4: EXAME FÍSICO, HIPOTROFISMO SEGMENTADO, PERIMETRIA PADRONIZADA E TESTES
    # ------------------------------------------------------------
    with t_fisico:
        with st.container(border=True):
            secao(
                "👁️ Inspeção, Hipotrofismo Segmentado e Palpação Detalhada (Direito × Esquerdo)",
                "Hipotrofismo avaliado separadamente para Quadríceps, Isquiotibiais e Tríceps Sural."
            )

            op_mar = ["Normal", "Antálgica", "Claudicante", "Marcha em Flexo de Joelho", "Uso de dispositivo auxiliar (Muleta/Bengala)"]
            marcha = st.selectbox("🚶 Padrão Global de Marcha", op_mar, index=get_idx(op_mar, "Marcha"), key=chave_widget(st.session_state, 'avaliacao:marcha'))

            st.markdown("<hr style='margin: 14px 0;'>", unsafe_allow_html=True)

            op_der = ["Ausente", "Vestígio (Onda +)", "Leve (1+)", "Moderado (2+)", "Grave / Tenso (3+)"]
            op_ali = ["Normal", "Valgo", "Varo", "Recurvatum", "Flexo"]
            op_hipo = ["Normal", "Hipotrofia Leve", "Hipotrofia Moderada", "Hipotrofia Severa"]

            # Estruturas dolorosas do joelho detalhadas conforme solicitado
            op_palp = [
                "Nenhuma / Indolor",
                "Pólo Superior da Patela (Tendão Quadricipital)",
                "Corpo / Facetas Patelares",
                "Pólo Inferior da Patela (Ápice)",
                "Corpo do Tendão Patelar",
                "Tuberosidade Anterior da Tíbia (TAT)",
                "Gordura de Hoffa (Infrapatelar)",
                "Retináculo Patelar Medial",
                "Retináculo Patelar Lateral",
                "Interlinha Articular Medial",
                "Interlinha Articular Lateral",
                "Pata de Ganso (Sartório/Grácil/Semitendíneo)",
                "Ligamento Colateral Medial (LCM)",
                "Ligamento Colateral Lateral (LCL)",
                "Trato Iliotibial / Tubérculo de Gerdy / Epicôndilo Lateral",
                "Tendão do Bíceps Femoral / Cabeça da Fíbula",
                "Tendões Isquiotibiais Mediais (Semimembranáceo/Semitendíneo)",
                "Fossa Poplítea / Gastrocnêmios",
            ]
            op_godet = ["Negativo", "Positivo"]
            op_temp = ["Normal", "Aumentada (Calor local)", "Diminuída"]

            col_fis_d, col_fis_e = st.columns(2, gap="large")

            # --- COLUNA MEMBRO DIREITO ---
            with col_fis_d:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-bottom: 8px;'>🦵 Membro Inferior DIREITO</h4>", unsafe_allow_html=True)
                derrame_d = st.selectbox("Derrame Articular — Direito", op_der, index=get_idx(op_der, "Derrame_Dir", "Derrame"), key="der_d")
                alinhamento_d = st.selectbox("Alinhamento Estático — Direito", op_ali, index=get_idx(op_ali, "Alinhamento_Dir", "Alinhamento"), key="ali_d")

                st.caption("🔍 Sinais de Hipotrofismo Muscular — Direito")
                ch_d1, ch_d2, ch_d3 = st.columns(3)
                hipo_quad_d = ch_d1.selectbox("Quadríceps (D)", op_hipo, index=get_idx(op_hipo, "Hipo_Quad_Dir", "Trofismo_Dir"), key="hq_d")
                hipo_isq_d = ch_d2.selectbox("Isquiotibiais (D)", op_hipo, index=get_idx(op_hipo, "Hipo_Isq_Dir"), key="hi_d")
                hipo_tri_d = ch_d3.selectbox("Tríceps Sural (D)", op_hipo, index=get_idx(op_hipo, "Hipo_Tri_Dir"), key="ht_d")

                palpacao_d = st.multiselect(
                    "Estruturas Dolorosas à Palpação — Direito",
                    op_palp,
                    default=get_list(op_palp, "Palpacao_Dir") or get_list(op_palp, "Palpacao"),
                    key="palp_d",
                )
                c_gd1, c_gd2 = st.columns(2)
                with c_gd1:
                    godet_d = st.radio("Sinal de Godet (Dir)", op_godet, index=get_idx(op_godet, "Godet_Dir", "Godet"), key="god_d")
                with c_gd2:
                    temp_d = st.radio("Temperatura (Dir)", op_temp, index=get_idx(op_temp, "Temperatura_Dir", "Temperatura"), key="tmp_d")

            # --- COLUNA MEMBRO ESQUERDO ---
            with col_fis_e:
                st.markdown(f"<h4 style='color: {CORES_GENUA['secundaria']}; margin-bottom: 8px;'>🦵 Membro Inferior ESQUERDO</h4>", unsafe_allow_html=True)
                derrame_e = st.selectbox("Derrame Articular — Esquerdo", op_der, index=get_idx(op_der, "Derrame_Esq", "Derrame"), key="der_e")
                alinhamento_e = st.selectbox("Alinhamento Estático — Esquerdo", op_ali, index=get_idx(op_ali, "Alinhamento_Esq", "Alinhamento"), key="ali_e")

                st.caption("🔍 Sinais de Hipotrofismo Muscular — Esquerdo")
                ch_e1, ch_e2, ch_e3 = st.columns(3)
                hipo_quad_e = ch_e1.selectbox("Quadríceps (E)", op_hipo, index=get_idx(op_hipo, "Hipo_Quad_Esq", "Trofismo_Esq"), key="hq_e")
                hipo_isq_e = ch_e2.selectbox("Isquiotibiais (E)", op_hipo, index=get_idx(op_hipo, "Hipo_Isq_Esq"), key="hi_e")
                hipo_tri_e = ch_e3.selectbox("Tríceps Sural (E)", op_hipo, index=get_idx(op_hipo, "Hipo_Tri_Esq"), key="ht_e")

                palpacao_e = st.multiselect(
                    "Estruturas Dolorosas à Palpação — Esquerdo",
                    op_palp,
                    default=get_list(op_palp, "Palpacao_Esq") or get_list(op_palp, "Palpacao"),
                    key="palp_e",
                )
                c_ge1, c_ge2 = st.columns(2)
                with c_ge1:
                    godet_e = st.radio("Sinal de Godet (Esq)", op_godet, index=get_idx(op_godet, "Godet_Esq", "Godet"), key="god_e")
                with c_ge2:
                    temp_e = st.radio("Temperatura (Esq)", op_temp, index=get_idx(op_temp, "Temperatura_Esq", "Temperatura"), key="tmp_e")

        # Card 2 da Aba Físico: Perimetria de Coxa (4 medidas de 5 em 5 cm) e Perna/Panturrilha (3 medidas de 5 em 5 cm)
        with st.container(border=True):
            secao(
                "📏 Perimetria Segmentar Padronizada (Coxa e Panturrilha — Direito × Esquerdo)",
                "Coxa: 4 medidas supra-patelares de 5 em 5 cm (+5, +10, +15 e +20 cm) | Perna/Panturrilha: 3 medidas infra-patelares de 5 em 5 cm (-5, -10 e -15 cm)."
            )
            perim_salva = dados.get("Perimetria_Detalhada") if isinstance(dados.get("Perimetria_Detalhada"), dict) else {}

            def _get_perim(chave_p, fallback_val=0.0):
                try:
                    return float(perim_salva.get(chave_p, fallback_val) or fallback_val)
                except Exception:
                    return 0.0

            st.markdown("**1. Perimetria de Coxa (cm — Acima do pólo superior da patela)**")
            ccx1, ccx2, ccx3, ccx4 = st.columns(4)
            coxa_5_d = ccx1.number_input("Coxa +5 cm (Dir)", 0.0, 100.0, _get_perim("coxa_5_d"), 0.5, key="cx5d")
            coxa_10_d = ccx2.number_input("Coxa +10 cm (Dir)", 0.0, 100.0, _get_perim("coxa_10_d", float(dados.get("Perimetria_Dir_cm", 0.0) or 0.0)), 0.5, key="cx10d")
            coxa_15_d = ccx3.number_input("Coxa +15 cm (Dir)", 0.0, 100.0, _get_perim("coxa_15_d"), 0.5, key="cx15d")
            coxa_20_d = ccx4.number_input("Coxa +20 cm (Dir)", 0.0, 100.0, _get_perim("coxa_20_d"), 0.5, key="cx20d")

            ccx5, ccx6, ccx7, ccx8 = st.columns(4)
            coxa_5_e = ccx5.number_input("Coxa +5 cm (Esq)", 0.0, 100.0, _get_perim("coxa_5_e"), 0.5, key="cx5e")
            coxa_10_e = ccx6.number_input("Coxa +10 cm (Esq)", 0.0, 100.0, _get_perim("coxa_10_e", float(dados.get("Perimetria_Esq_cm", 0.0) or 0.0)), 0.5, key="cx10e")
            coxa_15_e = ccx7.number_input("Coxa +15 cm (Esq)", 0.0, 100.0, _get_perim("coxa_15_e"), 0.5, key="cx15e")
            coxa_20_e = ccx8.number_input("Coxa +20 cm (Esq)", 0.0, 100.0, _get_perim("coxa_20_e"), 0.5, key="cx20e")

            st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
            st.markdown("**2. Perimetria de Perna / Panturrilha (cm — Abaixo da interlinha/TAT)**")
            cpn1, cpn2, cpn3 = st.columns(3)
            perna_5_d = cpn1.number_input("Perna -5 cm (Dir)", 0.0, 100.0, _get_perim("perna_5_d"), 0.5, key="pn5d")
            perna_10_d = cpn2.number_input("Perna -10 cm (Dir)", 0.0, 100.0, _get_perim("perna_10_d"), 0.5, key="pn10d")
            perna_15_d = cpn3.number_input("Perna -15 cm (Dir)", 0.0, 100.0, _get_perim("perna_15_d"), 0.5, key="pn15d")

            cpn4, cpn5, cpn6 = st.columns(3)
            perna_5_e = cpn4.number_input("Perna -5 cm (Esq)", 0.0, 100.0, _get_perim("perna_5_e"), 0.5, key="pn5e")
            perna_10_e = cpn5.number_input("Perna -10 cm (Esq)", 0.0, 100.0, _get_perim("perna_10_e"), 0.5, key="pn10e")
            perna_15_e = cpn6.number_input("Perna -15 cm (Esq)", 0.0, 100.0, _get_perim("perna_15_e"), 0.5, key="pn15e")

            if coxa_10_d > 0 and coxa_10_e > 0:
                diff_perim = coxa_10_d - coxa_10_e
                if abs(diff_perim) >= 1.5:
                    menor_lado = "Direita" if diff_perim < 0 else "Esquerda"
                    st.warning(f"⚠️ **Assimetria em Coxa (+10 cm):** Diferença de **{abs(diff_perim):.1f} cm** (menor na coxa **{menor_lado}** — relevância clínica ≥ 1,5 cm).")

            c_pele, c_perim_obs = st.columns(2)
            op_pele = ["Nenhuma", "Equimose", "Hematoma", "Cicatrizes Cirúrgicas", "Aderência Cicatricial", "Fístulas"]
            with c_pele:
                pele = st.multiselect("Alterações Cutâneas / Cicatriciais", op_pele, default=get_list(op_pele, "Pele"), key=chave_widget(st.session_state, 'avaliacao:pele'))
            with c_perim_obs:
                perimetria_obs = st.text_input(
                    "Notas Adicionais de Perimetria / Edema",
                    value=dados.get("Perimetria_Obs", ""),
                    placeholder="Ex: Edema residual perimaleolar ou supra-patelar",
                    key=chave_widget(st.session_state, 'avaliacao:perimetria_obs'),
                )
        # Card 3 da Aba Físico: Testes Especiais (Retirado Decline Squat, Adicionado Compressão Patelar)
        with st.container(border=True):
            secao(
                "🧪 Testes Especiais Ortopédicos (Separados por Joelho: Direito × Esquerdo)",
                "Clusters diagnósticos ligamentares, meniscais e femoropatelares (incluindo Compressão Patelar)."
            )
            op_lig = ["Nenhum", "Lachman", "Gaveta Anterior", "Gaveta Posterior", "Estresse Valgo", "Estresse Varo", "Pivot Shift", "Dial Test"]
            op_men = ["Nenhum", "Ege", "Thessaly (20°)", "McMurray", "Apley", "Sensibilidade Interlinha (JLT)"]
            op_pat = [
                "Nenhum",
                "Teste de Compressão Patelar",
                "Step Up Doloroso",
                "Step Down Doloroso",
                "Extensão CCA Dolorosa",
                "Sinal de Clarke",
                "Apreensão Patelar",
                "Teste de Noble (Trato Iliotibial)",
            ]

            c_te_d, c_te_e = st.columns(2, gap="large")
            with c_te_d:
                st.markdown("**🦵 Joelho DIREITO (Marcar Positivos)**")
                t_lig_d = st.multiselect("🔗 Ligamentares (Direito)", op_lig, default=get_list(op_lig, "Testes_Ligamentares_Dir") or get_list(op_lig, "Testes_Ligamentares"), key="t_lig_d")
                t_men_d = st.multiselect("🌙 Meniscais (Direito)", op_men, default=get_list(op_men, "Testes_Meniscais_Dir") or get_list(op_men, "Testes_Meniscais"), key="t_men_d")
                t_pat_d = st.multiselect("🎯 Femoropatelares / Tendíneos (Direito)", op_pat, default=get_list(op_pat, "Testes_Femoropatelar_Dir") or get_list(op_pat, "Testes_Femoropatelar"), key="t_pat_d")

            with c_te_e:
                st.markdown("**🦵 Joelho ESQUERDO (Marcar Positivos)**")
                t_lig_e = st.multiselect("🔗 Ligamentares (Esquerdo)", op_lig, default=get_list(op_lig, "Testes_Ligamentares_Esq"), key="t_lig_e")
                t_men_e = st.multiselect("🌙 Meniscais (Esquerdo)", op_men, default=get_list(op_men, "Testes_Meniscais_Esq"), key="t_men_e")
                t_pat_e = st.multiselect("🎯 Femoropatelares / Tendíneos (Esquerdo)", op_pat, default=get_list(op_pat, "Testes_Femoropatelar_Esq"), key="t_pat_e")

    # ------------------------------------------------------------
    # ABA 5: AVALIAÇÃO FUNCIONAL, FORÇA OPCIONAL (LSI + I:Q), CONTROLE MOTOR (DOR) E FLEXIBILIDADE
    # ------------------------------------------------------------
    with t_funcional:
        def get_val_str(chave_db, prefix, default, tipo=int):
            try:
                val = dados.get(chave_db, "")
                if not val:
                    return default
                parts = val.replace(" | ", " ").split()
                for p in parts:
                    if p.startswith(prefix + ":"):
                        return tipo(p.split(":")[1])
            except (ValueError, TypeError, AttributeError):
                pass
            return default

        # Card 1: Força Muscular Opcional (Pós-Op vs Oxford vs Dinamometria) + LSI + Razão I:Q
        with st.container(border=True):
            secao(
                "💪 Avaliação de Força Muscular (Opcional por Fase Clínica / Fenótipo)",
                "Escolha se a força será avaliada por Dinamometria (kgf), Escala Manual de Oxford (0-5) ou Omitida (ex: Pós-Operatório imediato)."
            )
            op_modo_forca = [
                "Dinamometria Isométrica (kgf)",
                "Escala Manual de Oxford (0 a 5)",
                "Não Aplicável / Pós-Op Agudo (Proteção Tecidual)",
            ]
            default_idx_forca = 2 if "Pós-Operatório Agudo" in fenotipo_clinico and not dados.get("Modo_Avaliacao_Forca") else get_idx(op_modo_forca, "Modo_Avaliacao_Forca")
            modo_forca = st.radio(
                "Selecione o Método de Avaliação de Força nesta Consulta:",
                op_modo_forca,
                index=default_idx_forca,
                horizontal=True,
                key=chave_widget(st.session_state, 'avaliacao:modo_forca'),
            )
            # Inicializa valores padrão seguros
            fg_ext_d = fg_flex_d = fg_abd_d = fg_add_d = 5
            fg_ext_e = fg_flex_e = fg_abd_e = fg_add_e = 5
            din_ext_d = get_val_str("Dinamometria_Dir", "Ext", 0.0, float)
            din_flex_d = get_val_str("Dinamometria_Dir", "Flex", 0.0, float)
            din_abd_d = get_val_str("Dinamometria_Dir", "Abd", 0.0, float)
            din_add_d = get_val_str("Dinamometria_Dir", "Add", 0.0, float)
            din_ext_e = get_val_str("Dinamometria_Esq", "Ext", 0.0, float)
            din_flex_e = get_val_str("Dinamometria_Esq", "Flex", 0.0, float)
            din_abd_e = get_val_str("Dinamometria_Esq", "Abd", 0.0, float)
            din_add_e = get_val_str("Dinamometria_Esq", "Add", 0.0, float)
            resumo_lsi_iq_str = "Não aplicável"

            if modo_forca == "Não Aplicável / Pós-Op Agudo (Proteção Tecidual)":
                st.info("🛡️ **Modo Pós-Operatório / Proteção Tecidual Ativo:** Avaliação de força máxima omitida com segurança para respeitar a cicatrização biológica.")
                din_ext_d = din_flex_d = din_abd_d = din_add_d = 0.0
                din_ext_e = din_flex_e = din_abd_e = din_add_e = 0.0

            elif modo_forca == "Escala Manual de Oxford (0 a 5)":
                st.caption("Força Manual Qualitativa (Escala de Oxford 0 a 5 — Triagem Clínica)")
                c_fg1, c_fg2, c_fg3, c_fg4 = st.columns(4)
                fg_ext_d = c_fg1.number_input("Extensão (Dir) [0-5]", 0, 5, get_val_str("Forca_Geral_Dir", "Ext", 5), key=chave_widget(st.session_state, 'avaliacao:fg_ext_d'))
                fg_flex_d = c_fg2.number_input("Flexão (Dir) [0-5]", 0, 5, get_val_str("Forca_Geral_Dir", "Flex", 5), key=chave_widget(st.session_state, 'avaliacao:fg_flex_d'))
                fg_abd_d = c_fg3.number_input("Abdução (Dir) [0-5]", 0, 5, get_val_str("Forca_Geral_Dir", "Abd", 5), key=chave_widget(st.session_state, 'avaliacao:fg_abd_d'))
                fg_add_d = c_fg4.number_input("Adução (Dir) [0-5]", 0, 5, get_val_str("Forca_Geral_Dir", "Add", 5), key=chave_widget(st.session_state, 'avaliacao:fg_add_d'))

                c_fg5, c_fg6, c_fg7, c_fg8 = st.columns(4)
                fg_ext_e = c_fg5.number_input("Extensão (Esq) [0-5]", 0, 5, get_val_str("Forca_Geral_Esq", "Ext", 5), key=chave_widget(st.session_state, 'avaliacao:fg_ext_e'))
                fg_flex_e = c_fg6.number_input("Flexão (Esq) [0-5]", 0, 5, get_val_str("Forca_Geral_Esq", "Flex", 5), key=chave_widget(st.session_state, 'avaliacao:fg_flex_e'))
                fg_abd_e = c_fg7.number_input("Abdução (Esq) [0-5]", 0, 5, get_val_str("Forca_Geral_Esq", "Abd", 5), key=chave_widget(st.session_state, 'avaliacao:fg_abd_e'))
                fg_add_e = c_fg8.number_input("Adução (Esq) [0-5]", 0, 5, get_val_str("Forca_Geral_Esq", "Add", 5), key=chave_widget(st.session_state, 'avaliacao:fg_add_e'))

            else:
                st.caption("Dinamometria Quantitativa (Handheld Dynamometer — kgf) · Calcula LSI Bilateral e Razão I:Q (Isquiotibiais : Quadríceps)")
                c_din1, c_din2, c_din3, c_din4 = st.columns(4)
                din_ext_d = c_din1.number_input("Quadríceps / Ext Dir (kgf)", 0.0, 200.0, din_ext_d, 1.0, key=chave_widget(st.session_state, 'avaliacao:din_ext_d'))
                din_flex_d = c_din2.number_input("Isquios / Flex Dir (kgf)", 0.0, 200.0, din_flex_d, 1.0, key=chave_widget(st.session_state, 'avaliacao:din_flex_d'))
                din_abd_d = c_din3.number_input("Abdução Dir (kgf)", 0.0, 200.0, din_abd_d, 1.0, key=chave_widget(st.session_state, 'avaliacao:din_abd_d'))
                din_add_d = c_din4.number_input("Adução Dir (kgf)", 0.0, 200.0, din_add_d, 1.0, key=chave_widget(st.session_state, 'avaliacao:din_add_d'))

                c_din5, c_din6, c_din7, c_din8 = st.columns(4)
                din_ext_e = c_din5.number_input("Quadríceps / Ext Esq (kgf)", 0.0, 200.0, din_ext_e, 1.0, key=chave_widget(st.session_state, 'avaliacao:din_ext_e'))
                din_flex_e = c_din6.number_input("Isquios / Flex Esq (kgf)", 0.0, 200.0, din_flex_e, 1.0, key=chave_widget(st.session_state, 'avaliacao:din_flex_e'))
                din_abd_e = c_din7.number_input("Abdução Esq (kgf)", 0.0, 200.0, din_abd_e, 1.0, key=chave_widget(st.session_state, 'avaliacao:din_abd_e'))
                din_add_e = c_din8.number_input("Adução Esq (kgf)", 0.0, 200.0, din_add_e, 1.0, key=chave_widget(st.session_state, 'avaliacao:din_add_e'))

                # Cálculos aprimorados de LSI Bilateral e Razão I:Q (H:Q Ratio)
                pares_din = [
                    ("Quadríceps", din_ext_d, din_ext_e),
                    ("Isquiotibiais", din_flex_d, din_flex_e),
                    ("Abdutores", din_abd_d, din_abd_e),
                    ("Adutores", din_add_d, din_add_e),
                ]
                ativos_din = [(nome, d, e) for nome, d, e in pares_din if d > 0 or e > 0]
                partes_resumo_lsi = []
                if ativos_din:
                    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                    cols_lsi = st.columns(len(ativos_din))
                    for idx_l, (nome_g, val_d, val_e) in enumerate(ativos_din):
                        if "Direito" in lado_acometido or "Dir > Esq" in lado_acometido:
                            lesado, saudavel = val_d, val_e
                        elif "Esquerdo" in lado_acometido or "Esq > Dir" in lado_acometido:
                            lesado, saudavel = val_e, val_d
                        else:
                            lesado, saudavel = min(val_d, val_e), max(val_d, val_e)

                        lsi_g = (lesado / saudavel * 100.0) if saudavel > 0 else None
                        diff_kg = abs(val_d - val_e)
                        lsi_texto = f"{lsi_g:.0f}%" if lsi_g is not None else "N/D"
                        partes_resumo_lsi.append(f"LSI {nome_g}: {lsi_texto}")
                        with cols_lsi[idx_l]:
                            st.metric(
                                label=f"LSI {nome_g}",
                                value=lsi_texto,
                                delta=f"Δ {diff_kg:.1f} kgf",
                                delta_color="off" if lsi_g is None else ("normal" if lsi_g >= 90 else "inverse"),
                            )

                # Cálculo da Razão Isquiotibiais : Quadríceps (I:Q Ratio) para cada perna
                iq_dir = (din_flex_d / din_ext_d * 100.0) if (din_ext_d > 0 and din_flex_d > 0) else None
                iq_esq = (din_flex_e / din_ext_e * 100.0) if (din_ext_e > 0 and din_flex_e > 0) else None

                if iq_dir is not None or iq_esq is not None:
                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                    ciq1, ciq2 = st.columns(2)
                    if iq_dir is not None:
                        status_iq_d = "🟢 Equilíbrio Ideal (55-65%)" if 55 <= iq_dir <= 70 else ("🔴 Dominância Quadríceps (<55%)" if iq_dir < 55 else "🟡 Dominância Isquios (>70%)")
                        ciq1.metric("⚖️ Razão I:Q — Direito (Isquios/Quad)", f"{iq_dir:.0f}% ({iq_dir/100:.2f})", status_iq_d, delta_color="normal" if 55 <= iq_dir <= 70 else "inverse")
                        partes_resumo_lsi.append(f"Razao I:Q Dir: {iq_dir:.0f}%")
                    if iq_esq is not None:
                        status_iq_e = "🟢 Equilíbrio Ideal (55-65%)" if 55 <= iq_esq <= 70 else ("🔴 Dominância Quadríceps (<55%)" if iq_esq < 55 else "🟡 Dominância Isquios (>70%)")
                        ciq2.metric("⚖️ Razão I:Q — Esquerdo (Isquios/Quad)", f"{iq_esq:.0f}% ({iq_esq/100:.2f})", status_iq_e, delta_color="normal" if 55 <= iq_esq <= 70 else "inverse")
                        partes_resumo_lsi.append(f"Razao I:Q Esq: {iq_esq:.0f}%")

                resumo_lsi_iq_str = " | ".join(partes_resumo_lsi) if partes_resumo_lsi else "Não medido"

        # Card 2: Mobilidade Articular (Goniometria e Lunge Test)
        with st.container(border=True):
            secao("📐 Mobilidade Articular (Goniometria e Lunge Test)", "Amplitude de movimento ativa/passiva de joelho e dorsiflexão em cadeia fechada.")
            c_flex1, c_flex2, c_ext1, c_ext2 = st.columns(4)
            adm_flex_d = c_flex1.number_input("Flexão (Dir) °", 0.0, 160.0, get_val_str("ADM_Joelho_Flexao", "Dir", 0.0, float), 1.0, key="adm_flex_d")
            adm_flex_e = c_flex2.number_input("Flexão (Esq) °", 0.0, 160.0, get_val_str("ADM_Joelho_Flexao", "Esq", 0.0, float), 1.0, key="adm_flex_e")
            adm_ext_d = c_ext1.number_input("Extensão (Dir) °", -15.0, 30.0, get_val_str("ADM_Joelho_Extensao", "Dir", 0.0, float), 1.0, key="adm_ext_d")
            adm_ext_e = c_ext2.number_input("Extensão (Esq) °", -15.0, 30.0, get_val_str("ADM_Joelho_Extensao", "Esq", 0.0, float), 1.0, key="adm_ext_e")

            st.markdown("<hr style='margin: 14px 0;'>", unsafe_allow_html=True)
            c_lunge1, c_lunge2 = st.columns(2)
            lunge_d = c_lunge1.number_input("Lunge Test — Tornozelo Direito (cm)", 0.0, 30.0, get_val_str("Lunge_Test", "Dir", 0.0, float), 0.5, key="lunge_d")
            lunge_e = c_lunge2.number_input("Lunge Test — Tornozelo Esquerdo (cm)", 0.0, 30.0, get_val_str("Lunge_Test", "Esq", 0.0, float), 0.5, key="lunge_e")

        # Card 3: Controle Motor Opcional (Foco na Relação Funcionalidade x Dor igual ao Check-in) + Flexibilidade (Glúteo e Adutores)
        with st.container(border=True):
            secao(
                "⚙️ Controle Motor & Relação Funcionalidade × Dor (Opcional para Pós-Op)",
                "Avalia se o gesto funcional ocorre sem dor ou com dor (igual ao Check-in), sem penalizar pacientes em Pós-Op com 'ruim/incapaz' quando ainda não têm liberação para correr ou saltar."
            )
            avaliar_cm_bool = st.checkbox(
                "✅ Habilitar Avaliação de Gestos Funcionais / Controle Motor nesta consulta",
                value=bool(dados.get("Avaliar_Controle_Motor", "Pós-Operatório Agudo" not in fenotipo_clinico)),
                key=chave_widget(st.session_state, 'avaliacao:avaliar_cm_bool'),
            )
            opcoes_dor_cm = [
                "Não Aplicável (Fase Pós-Op)",
                "Sem Dor (0)",
                "Dor Leve (1 - 3)",
                "Dor Moderada (4 - 7)",
                "Dor Grave (8 - 10)",
            ]
            cm_salvo_dict = dados.get("CM_Dor_Dict") if isinstance(dados.get("CM_Dor_Dict"), dict) else {}

            def _idx_cm_dor(chave_cm, padrao_idx=1):
                v = cm_salvo_dict.get(chave_cm)
                if v in opcoes_dor_cm:
                    return opcoes_dor_cm.index(v)
                return 0 if "Pós-Operatório Agudo" in fenotipo_clinico else padrao_idx

            novo_cm_dor_dict = {}
            if avaliar_cm_bool:
                cm1, cm2, cm3 = st.columns(3)
                with cm1:
                    st.caption("PADRÕES GLOBAIS")
                    cm_marcha = st.selectbox("Marcha", opcoes_dor_cm, index=_idx_cm_dor("Marcha", 1), key=chave_widget(st.session_state, 'avaliacao:cm_marcha'))
                    cm_agach_bi = st.selectbox("Agachamento Bipodal", opcoes_dor_cm, index=_idx_cm_dor("Agach_Bi", 1), key=chave_widget(st.session_state, 'avaliacao:cm_agach_bi'))
                    cm_corrida = st.selectbox("Corrida", opcoes_dor_cm, index=_idx_cm_dor("Corrida", 0), key=chave_widget(st.session_state, 'avaliacao:cm_corrida'))
                    cm_salto = st.selectbox("Salto Bipodal", opcoes_dor_cm, index=_idx_cm_dor("Salto", 0), key=chave_widget(st.session_state, 'avaliacao:cm_salto'))
                with cm2:
                    st.caption("MEMBRO DIREITO")
                    cm_agach_uni_d = st.selectbox("Agachamento Uni (D)", opcoes_dor_cm, index=_idx_cm_dor("Agach_D", 1), key=chave_widget(st.session_state, 'avaliacao:cm_agach_uni_d'))
                    cm_step_down_d = st.selectbox("Step Down (D)", opcoes_dor_cm, index=_idx_cm_dor("StepDown_D", 1), key=chave_widget(st.session_state, 'avaliacao:cm_step_down_d'))
                    cm_step_up_d = st.selectbox("Step Up (D)", opcoes_dor_cm, index=_idx_cm_dor("StepUp_D", 1), key=chave_widget(st.session_state, 'avaliacao:cm_step_up_d'))
                    cm_afundo_d = st.selectbox("Afundo (D)", opcoes_dor_cm, index=_idx_cm_dor("Afundo_D", 1), key=chave_widget(st.session_state, 'avaliacao:cm_afundo_d'))
                    cm_eq_uni_d = st.selectbox("Equilíbrio Uni (D)", opcoes_dor_cm, index=_idx_cm_dor("Eq_D", 1), key=chave_widget(st.session_state, 'avaliacao:cm_eq_uni_d'))
                with cm3:
                    st.caption("MEMBRO ESQUERDO")
                    cm_agach_uni_e = st.selectbox("Agachamento Uni (E)", opcoes_dor_cm, index=_idx_cm_dor("Agach_E", 1), key=chave_widget(st.session_state, 'avaliacao:cm_agach_uni_e'))
                    cm_step_down_e = st.selectbox("Step Down (E)", opcoes_dor_cm, index=_idx_cm_dor("StepDown_E", 1), key=chave_widget(st.session_state, 'avaliacao:cm_step_down_e'))
                    cm_step_up_e = st.selectbox("Step Up (E)", opcoes_dor_cm, index=_idx_cm_dor("StepUp_E", 1), key=chave_widget(st.session_state, 'avaliacao:cm_step_up_e'))
                    cm_afundo_e = st.selectbox("Afundo (E)", opcoes_dor_cm, index=_idx_cm_dor("Afundo_E", 1), key=chave_widget(st.session_state, 'avaliacao:cm_afundo_e'))
                    cm_eq_uni_e = st.selectbox("Equilíbrio Uni (E)", opcoes_dor_cm, index=_idx_cm_dor("Eq_E", 1), key=chave_widget(st.session_state, 'avaliacao:cm_eq_uni_e'))

                novo_cm_dor_dict = {
                    "Marcha": cm_marcha, "Agach_Bi": cm_agach_bi, "Corrida": cm_corrida, "Salto": cm_salto,
                    "Agach_D": cm_agach_uni_d, "StepDown_D": cm_step_down_d, "StepUp_D": cm_step_up_d, "Afundo_D": cm_afundo_d, "Eq_D": cm_eq_uni_d,
                    "Agach_E": cm_agach_uni_e, "StepDown_E": cm_step_down_e, "StepUp_E": cm_step_up_e, "Afundo_E": cm_afundo_e, "Eq_E": cm_eq_uni_e,
                }
                resumo_cm_str = f"Marcha: {cm_marcha} | Agach Bipodal: {cm_agach_bi} | StepDown D: {cm_step_down_d} | StepDown E: {cm_step_down_e}"
            else:
                st.info("ℹ️ Avaliação de Controle Motor / Impacto desativada para esta fase (Pós-Operatório / Proteção).")
                cm_marcha = cm_corrida = cm_salto = cm_agach_bi = "Não Aplicável (Fase Pós-Op)"
                cm_agach_uni_d = cm_step_down_d = cm_step_up_d = cm_afundo_d = cm_eq_uni_d = "Não Aplicável (Fase Pós-Op)"
                cm_agach_uni_e = cm_step_down_e = cm_step_up_e = cm_afundo_e = cm_eq_uni_e = "Não Aplicável (Fase Pós-Op)"
                resumo_cm_str = "Opcional / Não Aplicado (Fase de Proteção Pós-Operatória)"

            st.markdown("<hr style='margin: 16px 0;'>", unsafe_allow_html=True)
            # Flexibilidade: Adicionados Encurtamento de Glúteo e Encurtamento de Adutores
            op_flex = [
                "Nenhuma",
                "Encurtamento de Glúteo",
                "Encurtamento de Adutores",
                "Thomas (+) - Iliopsoas",
                "Thomas (+) - Reto Femoral",
                "Ely (+) - Reto Femoral",
                "Ober (+) - Trato Iliotibial",
                "Encurtamento Isquiotibiais (Ângulo Poplíteo)",
            ]
            c_flx_d, c_flx_e = st.columns(2)
            with c_flx_d:
                flexibilidade_d = st.multiselect(
                    "🧘 Flexibilidade / Encurtamentos — Membro DIREITO",
                    op_flex,
                    default=get_list(op_flex, "Flexibilidade_Dir") or get_list(op_flex, "Flexibilidade"),
                    key="flx_d",
                )
            with c_flx_e:
                flexibilidade_e = st.multiselect(
                    "🧘 Flexibilidade / Encurtamentos — Membro ESQUERDO",
                    op_flex,
                    default=get_list(op_flex, "Flexibilidade_Esq") or get_list(op_flex, "Flexibilidade"),
                    key="flx_e",
                )

            st.markdown("<hr style='margin: 18px 0;'>", unsafe_allow_html=True)
            secao(
                "🎯 Definir o que vai entrar no Check-in Diário (Parametrizável por Paciente / Pós-Op)",
                "Escolha apenas o que faz sentido monitorar no Check-in deste paciente. Se deixar vazio em um Pós-Op agudo, os testes de impacto não serão cobrados no Check-in."
            )
            lista_testes_disp = [
                "Marcha sem Muletas",
                "Extensão Ativa Terminal",
                "Agachamento Bipodal",
                "Agachamento Unipodal (D)",
                "Agachamento Unipodal (E)",
                "Step Up (D)",
                "Step Up (E)",
                "Step Down (D)",
                "Step Down (E)",
                "Lunge / Afundo",
                "Salto (Hop Test)",
                "Corrida",
            ]
            def_alvos = get_list("Testes_Alvo")
            for t_antigo in def_alvos:
                if t_antigo not in lista_testes_disp:
                    lista_testes_disp.append(t_antigo)
            if not def_alvos and "Pós-Operatório Agudo" not in fenotipo_clinico:
                def_alvos = ["Agachamento Bipodal", "Step Down (D)" if "Direito" in lado_acometido else "Step Down (E)"]
            testes_alvo = st.multiselect("Atividades / Testes que entrarão no Check-in Diário (Opcional):", lista_testes_disp, default=def_alvos, key=chave_widget(st.session_state, 'avaliacao:testes_alvo'))

    # ------------------------------------------------------------
    # ABA 6: EXAMES COMPLEMENTARES
    # ------------------------------------------------------------
    with t_exames:
        with st.container(border=True):
            secao("🩻 Exames Complementares e Imagem", "Registre os exames trazidos pelo paciente e os principais achados radiológicos.")
            op_exames = [
                "Nenhum", "Raio-X", "Ressonância Magnética (RM)",
                "Tomografia Computadorizada (TC)", "Ultrassonografia (USG)", "Eletroneuromiografia"
            ]
            tipos_exames = st.multiselect("Modalidades de Exame Apresentadas *", op_exames, default=get_list(op_exames, "Exames_Apresentados"), key=chave_widget(st.session_state, 'avaliacao:tipos_exames'))
            laudo_exames = st.text_area(
                "Laudo / Achados Estruturais Relevantes *",
                value=dados.get("Laudo_Exames", "Nenhum"),
                placeholder="Descreva os achados de imagem (especificando lado Direito/Esquerdo) ou mantenha 'Nenhum'.",
                height=140,
                key=chave_widget(st.session_state, 'avaliacao:laudo_exames'),
            )
    # ------------------------------------------------------------
    # ABA 7: QUESTIONÁRIOS (PROMs — VERSÕES QUICK + COMPLETAS POR DOMÍNIO)
    # ------------------------------------------------------------
    with t_quest:
        with st.container(border=True):
            secao(
                "📋 Questionários Validados de Joelho (PROMs — Quick & Domínios Completos)",
                "Selecione quais questionários foram aplicados hoje. Apenas os marcados abaixo entram no cálculo e no PDF."
            )

            opcoes_todos_proms = ["KOOS", "IKDC", "LEFS", "VISA-P", "Lysholm", "WOMAC"]
            default_proms_aplicados = _detectar_proms_legados(dados)
            proms_aplicados = st.multiselect(
                "✅ Questionários Aplicados nesta Avaliação:",
                options=opcoes_todos_proms,
                default=[p for p in default_proms_aplicados if p in opcoes_todos_proms],
                key=chave_widget(st.session_state, 'avaliacao:proms_aplicados'),
            )
            respostas_salvas = dados.get("Respostas_PROMs") if isinstance(dados.get("Respostas_PROMs"), dict) else {}

            def _idx_prom(lista_op, chave_item, idx_padrao=0):
                val_salvo = respostas_salvas.get(chave_item)
                return lista_op.index(val_salvo) if val_salvo in lista_op else idx_padrao

            def _val_prom(chave_item, val_padrao):
                val_salvo = respostas_salvas.get(chave_item)
                try:
                    return int(val_salvo) if val_salvo is not None else val_padrao
                except Exception:
                    return val_padrao

            novas_respostas_proms = dict(respostas_salvas)

            # 1. KOOS-12 Completo (Dor, Sintomas/Rigidez, AVDs/Esporte e Qualidade de Vida)
            with st.expander("🟢 KOOS-12 / Domínios Completos (Lesões de Joelho, LCA, Menisco, Condropatia e OA)", expanded=("KOOS" in proms_aplicados)):
                koos_op = {"Extremo / Sempre (0)": 0, "Severo / Frequente (1)": 1, "Moderado (2)": 2, "Leve / Raro (3)": 3, "Nenhum / Nunca (4)": 4}
                lista_k_op = list(koos_op.keys())
                perguntas_koos12 = [
                    ("k1", "1. Sintomas: Inchaço / Efusão no joelho"),
                    ("k2", "2. Sintomas: Estalidos, rangidos ou travamento ao mover"),
                    ("k3", "3. Sintomas: Rigidez matinal ou após ficar sentado"),
                    ("k4", "4. Dor: Frequência com que sente dor no joelho"),
                    ("k5", "5. Dor: Ao girar/torcer sobre o joelho"),
                    ("k6", "6. Dor: Ao esticar totalmente ou dobrar totalmente o joelho"),
                    ("k7", "7. Dor: Ao subir ou descer escadas"),
                    ("k8", "8. Função (AVDs): Levantar-se de uma cadeira ou entrar/sair do carro"),
                    ("k9", "9. Função (AVDs): Ficar em pé ou caminhar em superfície plana"),
                    ("k10", "10. Esporte/Recreação: Agachar, correr ou saltar"),
                    ("k11", "11. Qualidade de Vida: Modificou seu estilo de vida para evitar sobrecarga no joelho?"),
                    ("k12", "12. Qualidade de Vida: Falta de confiança no joelho no dia a dia"),
                ]
                ck1, ck2 = st.columns(2)
                score_koos_bruto = 0
                for idx_k, (ch_k, label_k) in enumerate(perguntas_koos12):
                    with (ck1 if idx_k < 6 else ck2):
                        esc_k = st.selectbox(label_k, lista_k_op, index=_idx_prom(lista_k_op, ch_k, 4), key=ch_k)
                        novas_respostas_proms[ch_k] = esc_k
                        score_koos_bruto += koos_op[esc_k]

                pct_koos_calc = (score_koos_bruto / (len(perguntas_koos12) * 4)) * 100.0
                interp_koos_calc = "🚨 Risco Funcional" if pct_koos_calc < 40 else "🟡 Limitação Moderada" if pct_koos_calc < 80 else "🟢 Alta Performance"
                st.info(f"📊 **Resultado KOOS-12:** **{pct_koos_calc:.1f}%** — {interp_koos_calc} *(MCID: 8-10 pts | Roos 2003)*")

            # 2. IKDC Subjetivo Ampliado
            with st.expander("✚ IKDC Subjetivo (Avaliação Ligamentar, Meniscal e Cartilaginosa)", expanded=("IKDC" in proms_aplicados)):
                c_ik1, c_ik2 = st.columns(2)
                op_ik_freq = ["Constante (0 pts)", "Diária (2 pts)", "Semanal (4 pts)", "Rara (7 pts)", "Nenhuma (10 pts)"]
                op_ik_at = ["Incapaz (0 pts)", "Atividades Leves (3 pts)", "Moderadas / Corrida leve (6 pts)", "Esporte Intenso / Corte e Giro (10 pts)"]
                with c_ik1:
                    ik_dor = st.slider("1. Nível de Alívio de Dor (0=Dor insuportável, 10=Sem dor)", 0, 10, _val_prom("ik1", 10), key="ik1")
                    ik_freq = st.selectbox("2. Frequência da Dor", op_ik_freq, index=_idx_prom(op_ik_freq, "ik2", 4), key="ik2")
                    ik_at_nivel = st.selectbox("3. Nível de atividade que consegue realizar sem dor/falseio", op_ik_at, index=_idx_prom(op_ik_at, "ik_at", 3), key="ik_at")
                with c_ik2:
                    ik_func = st.slider("4. Função do Joelho Antes da Lesão (0-10)", 0, 10, _val_prom("ik3", 10), key="ik3")
                    ik_func_atual = st.slider("5. Função Global do Joelho Hoje (0-10)", 0, 10, _val_prom("ik4", 5), key="ik4")

                ik_pts_freq = 0 if "(0 pts)" in ik_freq else 2 if "(2 pts)" in ik_freq else 4 if "(4 pts)" in ik_freq else 7 if "(7 pts)" in ik_freq else 10
                ik_pts_at = 0 if "(0 pts)" in ik_at_nivel else 3 if "(3 pts)" in ik_at_nivel else 6 if "(6 pts)" in ik_at_nivel else 10
                for k_ik, v_ik in [("ik1", ik_dor), ("ik2", ik_freq), ("ik_at", ik_at_nivel), ("ik3", ik_func), ("ik4", ik_func_atual)]:
                    novas_respostas_proms[k_ik] = v_ik

                score_ikdc_calc = min(100.0, ((ik_dor + ik_pts_freq + ik_pts_at + (ik_func_atual * 2)) / 50.0) * 100.0)
                interp_ikdc_calc = "🚨 Baixa Função Subjetiva" if score_ikdc_calc < 60 else "🟡 Desempenho Moderado" if score_ikdc_calc < 85 else "🟢 Excelente Desempenho"
                st.info(f"📊 **Resultado IKDC:** **{score_ikdc_calc:.1f}%** — {interp_ikdc_calc} *(MCID: 9 pts | Irrgang 2006)*")

            # 3. LEFS
            with st.expander("📝 LEFS (Escala Funcional da Extremidade Inferior — 10 Atividades Chave)", expanded=("LEFS" in proms_aplicados)):
                opcoes_lefs = {
                    "Incapaz / Extrema Dificuldade": 0, "Muita Dificuldade": 1,
                    "Dificuldade Moderada": 2, "Um Pouco de Dificuldade": 3, "Nenhuma Dificuldade": 4
                }
                lista_k_lefs = list(opcoes_lefs.keys())
                perguntas_lefs = [
                    "1. Trabalho, tarefas domésticas ou escola",
                    "2. Agachar ou ajoelhar",
                    "3. Andar 2 quarteirões",
                    "4. Subir um lance de escadas",
                    "5. Descer um lance de escadas",
                    "6. Ficar em pé por 1 hora",
                    "7. Correr em terreno plano",
                    "8. Correr em terreno irregular",
                    "9. Saltar / Pular",
                    "10. Mudança rápida de direção (Corte)",
                ]
                score_lefs = 0
                c_l1, c_l2 = st.columns(2)
                for i, p in enumerate(perguntas_lefs):
                    with (c_l1 if i < 5 else c_l2):
                        esc_l = st.selectbox(p, lista_k_lefs, index=_idx_prom(lista_k_lefs, f"lefs_{i}", 0), key=f"lefs_{i}")
                        novas_respostas_proms[f"lefs_{i}"] = esc_l
                        score_lefs += opcoes_lefs[esc_l]

                pct_lefs_calc = (score_lefs / (len(perguntas_lefs) * 4)) * 100.0
                pts_lefs_80_calc = round((pct_lefs_calc / 100.0) * 80, 1)
                interp_lefs_calc = (
                    "🚨 Função Muito Ruim" if pct_lefs_calc < 30 else
                    "🟡 Função Regular" if pct_lefs_calc < 60 else
                    "🟢 Função Boa" if pct_lefs_calc < 85 else
                    "⭐ Função Excelente"
                )
                st.info(f"📊 **Resultado LEFS:** {pts_lefs_80_calc}/80 pts equivalentes (**{pct_lefs_calc:.1f}%**) — {interp_lefs_calc} *(MCID: 9 pts | Binkley 1999)*")

            # 4. VISA-P (8 itens oficiais completos)
            with st.expander("🎯 VISA-P Completo (Tendinopatia Patelar — 8 itens oficiais)", expanded=("VISA-P" in proms_aplicados)):
                c_v1, c_v2 = st.columns(2)
                with c_v1:
                    vp1 = st.slider("1. Minutos sentado sem dor (0-10)", 0, 10, _val_prom("vp1", 10), key="vp1")
                    vp2 = st.slider("2. Dor ao descer escadas em ritmo normal", 0, 10, _val_prom("vp2", 10), key="vp2")
                    vp3 = st.slider("3. Dor ao estender ativamente o joelho sem peso", 0, 10, _val_prom("vp3", 10), key="vp3")
                    vp4 = st.slider("4. Dor ao fazer afundo (lunge) com descarga de peso", 0, 10, _val_prom("vp4", 10), key="vp4")
                with c_v2:
                    vp5 = st.slider("5. Problemas para agachar totalmente", 0, 10, _val_prom("vp5", 10), key="vp5")
                    vp6 = st.slider("6. Dor durante/após 10 saltos unipodais", 0, 10, _val_prom("vp6", 10), key="vp6")
                    op_vp7 = ["Não consegue (0 pts)", "Treino modificado (4 pts)", "Treino completo mas nível reduzido (7 pts)", "Competindo no mesmo nível ou maior (10 pts)"]
                    p7 = st.selectbox("7. Prática Esportiva Atual", op_vp7, index=_idx_prom(op_vp7, "vp7", 0), key="vp7")
                    op_vp8 = ["Dor impede o treino (0 pts)", "Treina até 15 min antes de parar (7 pts)", "Treina com dor suportável (15 pts)", "Treina sem nenhuma dor (30 pts)"]
                    p8 = st.selectbox("8. Tempo de tolerância ao treino/esporte", op_vp8, index=_idx_prom(op_vp8, "vp8", 0), key="vp8")

                for k_vp, v_vp in [("vp1", vp1), ("vp2", vp2), ("vp3", vp3), ("vp4", vp4), ("vp5", vp5), ("vp6", vp6), ("vp7", p7), ("vp8", p8)]:
                    novas_respostas_proms[k_vp] = v_vp

                score_visap_calc = vp1 + vp2 + vp3 + vp4 + vp5 + vp6
                score_visap_calc += 0 if "(0 pts)" in p7 else 4 if "(4 pts)" in p7 else 7 if "(7 pts)" in p7 else 10
                score_visap_calc += 0 if "(0 pts)" in p8 else 7 if "(7 pts)" in p8 else 15 if "(15 pts)" in p8 else 30
                interp_visap_calc = "🚨 Tendinopatia Severa/Aguda" if score_visap_calc < 50 else "🟡 Fase Reativa" if score_visap_calc < 80 else "🟢 Remodelamento/Alta"
                st.info(f"📊 **Resultado VISA-P:** **{score_visap_calc}/100 pontos** — {interp_visap_calc} *(MCID: 13 pts | Hernandez-Sanchez 2014)*")

            # 5. LYSHOLM (8 itens oficiais completos)
            with st.expander("🦵 Escala de Lysholm Completa (8 domínios oficiais — 100 pts)", expanded=("Lysholm" in proms_aplicados)):
                c_ly1, c_ly2 = st.columns(2)
                op_ly_mancar = ["5 - Nenhum", "3 - Leve ou Periódico", "0 - Grave ou Constante"]
                op_ly_apoio = ["5 - Nenhum (Marcha livre)", "2 - Usa bengala ou muleta", "0 - Descarga de peso impossível"]
                op_ly_trav = ["15 - Nenhum travamento ou bloqueio", "10 - Sensação de fisgada sem bloqueio", "6 - Bloqueio ocasional", "2 - Bloqueio frequente", "0 - Articulação bloqueada no exame"]
                op_ly_inst = ["25 - Nunca falseia", "20 - Raramente no esporte intenso", "15 - Frequentemente no esporte intenso", "10 - Ocasionalmente nas AVDs", "5 - Frequentemente nas AVDs", "0 - A cada passo"]
                op_ly_dor = ["25 - Nenhuma", "20 - Inconstante e leve no exercício intenso", "15 - Marcada no exercício intenso", "10 - Marcada após caminhar > 2 km", "5 - Marcada após caminhar < 2 km", "0 - Constante"]
                op_ly_inc = ["10 - Nenhum", "6 - No exercício intenso", "2 - Nos esforços comuns / AVDs", "0 - Constante"]
                op_ly_esc = ["10 - Sem problemas", "6 - Levemente prejudicado", "2 - Um degrau de cada vez", "0 - Impossível"]
                op_ly_aga = ["5 - Sem problemas", "4 - Levemente prejudicado", "2 - Não passa de 90°", "0 - Impossível"]

                with c_ly1:
                    ly1 = st.selectbox("1. Claudicação (Mancar)", op_ly_mancar, index=_idx_prom(op_ly_mancar, "ly1", 0), key="ly1")
                    ly2 = st.selectbox("2. Apoio (Muletas/Bengala)", op_ly_apoio, index=_idx_prom(op_ly_apoio, "ly2", 0), key="ly2")
                    ly3 = st.selectbox("3. Bloqueio / Travamento", op_ly_trav, index=_idx_prom(op_ly_trav, "ly3", 0), key="ly3")
                    ly4 = st.selectbox("4. Instabilidade (Falseio)", op_ly_inst, index=_idx_prom(op_ly_inst, "ly4", 0), key="ly4")
                with c_ly2:
                    ly5 = st.selectbox("5. Dor", op_ly_dor, index=_idx_prom(op_ly_dor, "ly5", 0), key="ly5")
                    ly6 = st.selectbox("6. Edema / Inchaço", op_ly_inc, index=_idx_prom(op_ly_inc, "ly6", 0), key="ly6")
                    ly7 = st.selectbox("7. Subir Escadas", op_ly_esc, index=_idx_prom(op_ly_esc, "ly7", 0), key="ly7")
                    ly8 = st.selectbox("8. Agachamento", op_ly_aga, index=_idx_prom(op_ly_aga, "ly8", 0), key="ly8")

                lista_ly = [("ly1", ly1), ("ly2", ly2), ("ly3", ly3), ("ly4", ly4), ("ly5", ly5), ("ly6", ly6), ("ly7", ly7), ("ly8", ly8)]
                score_lysholm_calc = 0
                for k_ly, v_ly in lista_ly:
                    novas_respostas_proms[k_ly] = v_ly
                    score_lysholm_calc += int(v_ly.split(" -")[0])

                interp_lysholm_calc = "🚨 Ruim (<65)" if score_lysholm_calc < 65 else "🟡 Regular (65-83)" if score_lysholm_calc < 84 else "🟢 Bom (84-94)" if score_lysholm_calc < 95 else "⭐ Excelente (95-100)"
                st.info(f"📊 **Resultado Lysholm:** **{score_lysholm_calc}/100 pontos** — {interp_lysholm_calc} *(MCID: 10 pts | Briggs 2009)*")

            # 6. WOMAC
            with st.expander("🦴 Índice WOMAC (Osteoartrite — Dor, Rigidez e Função)", expanded=("WOMAC" in proms_aplicados)):
                w_op = {"Nenhuma": 0, "Leve": 1, "Moderada": 2, "Intensa": 3, "Muito Intensa": 4}
                lista_w_keys = list(w_op.keys())
                score_womac_bruto = 0
                c_w1, c_w2, c_w3 = st.columns(3)
                with c_w1:
                    st.markdown("**Dor (5 itens)**")
                    for p in ["Andar no plano", "Subir/descer escadas", "À noite na cama", "Sentar ou deitar", "Ficar em pé"]:
                        esc_w = st.selectbox(p, lista_w_keys, index=_idx_prom(lista_w_keys, f"wd_{p}", 0), key=f"wd_{p}")
                        novas_respostas_proms[f"wd_{p}"] = esc_w
                        score_womac_bruto += w_op[esc_w]
                with c_w2:
                    st.markdown("**Rigidez (2 itens)**")
                    for p in ["Rigidez matinal", "Rigidez ao final do dia"]:
                        esc_w = st.selectbox(p, lista_w_keys, index=_idx_prom(lista_w_keys, f"wr_{p}", 0), key=f"wr_{p}")
                        novas_respostas_proms[f"wr_{p}"] = esc_w
                        score_womac_bruto += w_op[esc_w]
                with c_w3:
                    st.markdown("**Função - AVDs (8 itens)**")
                    for p in ["Descer escadas", "Levantar da cadeira", "Ficar em pé", "Entrar/Sair do carro", "Calçar meias", "Sair da cama", "Entrar/sair do banho", "Tarefas domésticas"]:
                        esc_w = st.selectbox(p, lista_w_keys, index=_idx_prom(lista_w_keys, f"wf_{p}", 0), key=f"wf_{p}")
                        novas_respostas_proms[f"wf_{p}"] = esc_w
                        score_womac_bruto += w_op[esc_w]

                max_w = (5 + 2 + 8) * 4
                pct_womac_calc = 100.0 - ((score_womac_bruto / max_w) * 100.0)
                interp_womac_calc = "🚨 Limitação Severa" if pct_womac_calc < 30 else "🟡 Limitação Moderada" if pct_womac_calc < 70 else "🟢 Limitação Leve" if pct_womac_calc < 90 else "⭐ Excelente"
                st.info(f"📊 **Resultado WOMAC:** **{pct_womac_calc:.1f}%** — {interp_womac_calc}")

    # ============================================================
    # 5. COMPILAÇÃO DO PAYLOAD COMPLETO DA AVALIAÇÃO (PARA AUTO-SAVE, FIREBASE E PDF)
    # ============================================================
    def check_vazio(texto):
        return texto if texto and str(texto).strip() != "" else "Não relatado"

    if din_ext_d > 0 or din_ext_e > 0:
        if "Direito" in lado_acometido or "Dir > Esq" in lado_acometido:
            din_lesado, din_saudavel = float(din_ext_d), float(din_ext_e)
        elif "Esquerdo" in lado_acometido or "Esq > Dir" in lado_acometido:
            din_lesado, din_saudavel = float(din_ext_e), float(din_ext_d)
        else:
            din_lesado, din_saudavel = float(min(din_ext_d, din_ext_e)), float(max(din_ext_d, din_ext_e))
    else:
        din_lesado, din_saudavel = 0.0, 0.0

    pct_lefs_final = pct_lefs_calc if "LEFS" in proms_aplicados else 0.0
    pts_lefs_80_final = pts_lefs_80_calc if "LEFS" in proms_aplicados else 0.0
    interp_lefs_final = interp_lefs_calc if "LEFS" in proms_aplicados else "Não aplicado"

    score_visap_final = score_visap_calc if "VISA-P" in proms_aplicados else 0
    interp_visap_final = interp_visap_calc if "VISA-P" in proms_aplicados else "Não aplicado"

    score_lysholm_final = score_lysholm_calc if "Lysholm" in proms_aplicados else 0
    interp_lysholm_final = interp_lysholm_calc if "Lysholm" in proms_aplicados else "Não aplicado"

    pct_womac_final = pct_womac_calc if "WOMAC" in proms_aplicados else 0.0
    interp_womac_final = interp_womac_calc if "WOMAC" in proms_aplicados else "Não aplicado"

    pct_koos_final = pct_koos_calc if "KOOS" in proms_aplicados else 0.0
    score_ikdc_final = score_ikdc_calc if "IKDC" in proms_aplicados else 0.0

    hipo_resumo_d = f"Quad: {hipo_quad_d} | Isq: {hipo_isq_d} | Tríceps Sural: {hipo_tri_d}"
    hipo_resumo_e = f"Quad: {hipo_quad_e} | Isq: {hipo_isq_e} | Tríceps Sural: {hipo_tri_e}"

    perim_detalhada_dict = {
        "coxa_5_d": coxa_5_d, "coxa_10_d": coxa_10_d, "coxa_15_d": coxa_15_d, "coxa_20_d": coxa_20_d,
        "coxa_5_e": coxa_5_e, "coxa_10_e": coxa_10_e, "coxa_15_e": coxa_15_e, "coxa_20_e": coxa_20_e,
        "perna_5_d": perna_5_d, "perna_10_d": perna_10_d, "perna_15_d": perna_15_d,
        "perna_5_e": perna_5_e, "perna_10_e": perna_10_e, "perna_15_e": perna_15_e,
    }
    perim_coxa_resumo = (
        f"Dir (+5/+10/+15/+20cm): {coxa_5_d}/{coxa_10_d}/{coxa_15_d}/{coxa_20_d} cm | "
        f"Esq (+5/+10/+15/+20cm): {coxa_5_e}/{coxa_10_e}/{coxa_15_e}/{coxa_20_e} cm"
    )
    perim_perna_resumo = (
        f"Dir (-5/-10/-15cm): {perna_5_d}/{perna_10_d}/{perna_15_d} cm | "
        f"Esq (-5/-10/-15cm): {perna_5_e}/{perna_10_e}/{perna_15_e} cm"
    )

    t_lig_comb = f"Dir: {', '.join(t_lig_d) if t_lig_d else 'Nenhum'} | Esq: {', '.join(t_lig_e) if t_lig_e else 'Nenhum'}"
    t_men_comb = f"Dir: {', '.join(t_men_d) if t_men_d else 'Nenhum'} | Esq: {', '.join(t_men_e) if t_men_e else 'Nenhum'}"
    t_pat_comb = f"Dir: {', '.join(t_pat_d) if t_pat_d else 'Nenhum'} | Esq: {', '.join(t_pat_e) if t_pat_e else 'Nenhum'}"
    zonas_comb = f"Dir: {', '.join(zonas_dor_d) if zonas_dor_d else 'Nenhuma'} | Esq: {', '.join(zonas_dor_e) if zonas_dor_e else 'Nenhuma'}"
    flex_comb = f"Dir: {', '.join(flexibilidade_d) if flexibilidade_d else 'Normal'} | Esq: {', '.join(flexibilidade_e) if flexibilidade_e else 'Normal'}"

    dados_avaliacao = {
        "Data_Avaliacao": data_aval_input.strftime("%d/%m/%Y"),
        "Paciente": st.session_state.paciente,
        "Membro": st.session_state.get("membro_ativo", "Joelho"),
        "Lado_Acometido": lado_acometido,
        "Fenotipo_Clinico": fenotipo_clinico,
        "QP": qp,
        "HMA": check_vazio(hma),
        "Sinais_Sintomas": check_vazio(sinais_sintomas),
        "Fatores_Alivio": check_vazio(fat_alivio),
        "Fatores_Piora": check_vazio(fat_piora),
        "Tratamentos_Previos": check_vazio(trat_previos),
        "Conduta_Avaliacao": check_vazio(conduta_avaliacao),
        "Mapa_Dor": check_vazio(mapa_dor),
        "Pontos_Mapa_Dor": st.session_state.get("pontos_dor", []),
        "Laudo_Exames": check_vazio(laudo_exames),
        "Class_Dor": class_dor,
        "Origem_Dor": origem_dor,
        "Zonas_Dor_Dir": ", ".join(zonas_dor_d) if zonas_dor_d else "Nenhuma",
        "Zonas_Dor_Esq": ", ".join(zonas_dor_e) if zonas_dor_e else "Nenhuma",
        "Zonas_Dor": zonas_comb,
        "Red_Flags": ", ".join(red_flags) if red_flags else "Nenhuma",
        "Yellow_Cog": ", ".join(yellow_cog) if yellow_cog else "Nenhum",
        "Yellow_Flags": yellow_cog if yellow_cog else ["Nenhum"],
        "Sono": qualidade_sono,
        "Fatores_Sociais": ", ".join(fat_sociais) if fat_sociais else "Nenhum",
        "Blue_Flags": fat_sociais if fat_sociais else ["Nenhum"],
        "Comorbidades": ", ".join(comorbidades) if comorbidades else "Nenhuma",
        "Derrame_Dir": derrame_d,
        "Derrame_Esq": derrame_e,
        "Derrame": f"Dir: {derrame_d} | Esq: {derrame_e}",
        "Alinhamento_Dir": alinhamento_d,
        "Alinhamento_Esq": alinhamento_e,
        "Alinhamento": f"Dir: {alinhamento_d} | Esq: {alinhamento_e}",
        "Marcha": marcha,
        "Hipo_Quad_Dir": hipo_quad_d,
        "Hipo_Isq_Dir": hipo_isq_d,
        "Hipo_Tri_Dir": hipo_tri_d,
        "Hipo_Quad_Esq": hipo_quad_e,
        "Hipo_Isq_Esq": hipo_isq_e,
        "Hipo_Tri_Esq": hipo_tri_e,
        "Hipotrofismo_Detalhado_Dir": hipo_resumo_d,
        "Hipotrofismo_Detalhado_Esq": hipo_resumo_e,
        "Trofismo_Dir": hipo_quad_d,
        "Trofismo_Esq": hipo_quad_e,
        "Trofismo": f"Dir ({hipo_resumo_d}) | Esq ({hipo_resumo_e})",
        "Perimetria_Detalhada": perim_detalhada_dict,
        "Perimetria_Coxa_Resumo": perim_coxa_resumo,
        "Perimetria_Perna_Resumo": perim_perna_resumo,
        "Perimetria_Dir_cm": coxa_10_d,
        "Perimetria_Esq_cm": coxa_10_e,
        "Perimetria_Obs": perimetria_obs.strip(),
        "Perimetria": f"{perim_coxa_resumo} | {perim_perna_resumo}",
        "Pele": ", ".join(pele) if pele else "Normal",
        "Palpacao_Dir": ", ".join(palpacao_d) if palpacao_d else "Sem dor",
        "Palpacao_Esq": ", ".join(palpacao_e) if palpacao_e else "Sem dor",
        "Palpacao": f"Dir: {', '.join(palpacao_d) if palpacao_d else 'Sem dor'} | Esq: {', '.join(palpacao_e) if palpacao_e else 'Sem dor'}",
        "Godet_Dir": godet_d,
        "Godet_Esq": godet_e,
        "Godet": f"Dir: {godet_d} | Esq: {godet_e}",
        "Temperatura_Dir": temp_d,
        "Temperatura_Esq": temp_e,
        "Temperatura": f"Dir: {temp_d} | Esq: {temp_e}",
        "Testes_Ligamentares_Dir": ", ".join(t_lig_d) if t_lig_d else "Nenhum",
        "Testes_Ligamentares_Esq": ", ".join(t_lig_e) if t_lig_e else "Nenhum",
        "Testes_Ligamentares": t_lig_comb,
        "Testes_Meniscais_Dir": ", ".join(t_men_d) if t_men_d else "Nenhum",
        "Testes_Meniscais_Esq": ", ".join(t_men_e) if t_men_e else "Nenhum",
        "Testes_Meniscais": t_men_comb,
        "Testes_Femoropatelar_Dir": ", ".join(t_pat_d) if t_pat_d else "Nenhum",
        "Testes_Femoropatelar_Esq": ", ".join(t_pat_e) if t_pat_e else "Nenhum",
        "Testes_Femoropatelar": t_pat_comb,
        "Objetivo_Paciente": check_vazio(obj_paciente),
        "SANE_Baseline_Pct": sane_baseline,
        "Distancia_Objetivo_Pct": 100 - sane_baseline,
        "Modo_Avaliacao_Forca": modo_forca,
        "Forca_Geral_Dir": f"Ext:{fg_ext_d} Flex:{fg_flex_d} Abd:{fg_abd_d} Add:{fg_add_d}",
        "Forca_Geral_Esq": f"Ext:{fg_ext_e} Flex:{fg_flex_e} Abd:{fg_abd_e} Add:{fg_add_e}",
        "Dinamometria_Dir": f"Ext:{din_ext_d} Flex:{din_flex_d} Abd:{din_abd_d} Add:{din_add_d}",
        "Dinamometria_Esq": f"Ext:{din_ext_e} Flex:{din_flex_e} Abd:{din_abd_e} Add:{din_add_e}",
        "Dinamometria_Dict": {
            "ext_d": din_ext_d, "flex_d": din_flex_d, "abd_d": din_abd_d, "add_d": din_add_d,
            "ext_e": din_ext_e, "flex_e": din_flex_e, "abd_e": din_abd_e, "add_e": din_add_e,
        },
        "Resumo_LSI_IQ": resumo_lsi_iq_str,
        "Dinamometria_Lesado": din_lesado,
        "Dinamometria_Saudavel": din_saudavel,
        "ADM_Joelho_Flexao": f"Dir:{adm_flex_d} Esq:{adm_flex_e}",
        "ADM_Joelho_Extensao": f"Dir:{adm_ext_d} Esq:{adm_ext_e}",
        "Lunge_Test": f"Dir:{lunge_d} Esq:{lunge_e}",
        "Flexibilidade_Dir": ", ".join(flexibilidade_d) if flexibilidade_d else "Normal",
        "Flexibilidade_Esq": ", ".join(flexibilidade_e) if flexibilidade_e else "Normal",
        "Flexibilidade": flex_comb,
        "Avaliar_Controle_Motor": avaliar_cm_bool,
        "CM_Dor_Dict": novo_cm_dor_dict,
        "Resumo_Controle_Motor": resumo_cm_str,
        "CM_Globais": f"Marcha:{cm_marcha} | Corrida:{cm_corrida} | Salto:{cm_salto} | Agach_Bi:{cm_agach_bi}",
        "CM_Membro_Dir": f"Agach:{cm_agach_uni_d} | StepDown:{cm_step_down_d} | StepUp:{cm_step_up_d} | Afundo:{cm_afundo_d} | Eq:{cm_eq_uni_d}",
        "CM_Membro_Esq": f"Agach:{cm_agach_uni_e} | StepDown:{cm_step_down_e} | StepUp:{cm_step_up_e} | Afundo:{cm_afundo_e} | Eq:{cm_eq_uni_e}",
        "Exames_Apresentados": ", ".join(tipos_exames) if tipos_exames else "Nenhum",
        "Testes_Alvo": testes_alvo,
        "PROMs_Aplicados": proms_aplicados,
        "Respostas_PROMs": novas_respostas_proms if proms_aplicados else {},
        "LEFS_Pct": pct_lefs_final,
        "LEFS_Pts_80": pts_lefs_80_final,
        "Interpretacao_LEFS": interp_lefs_final,
        "VISA_P_Pts": score_visap_final,
        "Interpretacao_VISA_P": interp_visap_final,
        "Lysholm_Pts": score_lysholm_final,
        "Interpretacao_Lysholm": interp_lysholm_final,
        "WOMAC_Pct": pct_womac_final,
        "Interpretacao_WOMAC": interp_womac_final,
        "KOOS_Pct": pct_koos_final,
        "IKDC_Pct": score_ikdc_final,
        "Profissional_ID": st.session_state.get("user_email", "admin"),
    }

    # Atualiza o estado para o fragmento de Auto-Save a cada 5s
    st.session_state["_payload_avaliacao_atual"] = dados_avaliacao
    _fragmento_autosave_avaliacao()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # ============================================================
    # 6. BOTÕES DE SALVAMENTO MANUAL IMEDIATO & EXPORTAÇÃO EM PDF DA AVALIAÇÃO
    # ============================================================
    c_btn_save, c_btn_pdf = st.columns([1.4, 1.0], gap="medium")

    with c_btn_save:
        texto_botao = "🔄 SALVAR / ATUALIZAR AGORA" if st.session_state.get("doc_id_avaliacao") else "💾 SALVAR AVALIAÇÃO INICIAL"
        if st.button(texto_botao, width="stretch", type="primary"):
            if qp.strip() == "":
                toast("A 'Queixa Principal (QP)' na aba Anamnese é obrigatória para salvar o prontuário.", "error")
            else:
                if not payload_do_paciente_ativo(dados_avaliacao, st.session_state):
                    st.error("Salvamento bloqueado: o registro não pertence ao paciente ativo.")
                    return
                with st.spinner("Sincronizando Avaliação Inicial com o Firebase..."):
                    try:
                        if st.session_state.get("doc_id_avaliacao"):
                            db.collection("Avaliacao_Inicial").document(st.session_state.doc_id_avaliacao).set(dados_avaliacao, merge=True)
                        else:
                            _, novo_ref = db.collection("Avaliacao_Inicial").add(dados_avaliacao)
                            st.session_state.doc_id_avaliacao = novo_ref.id
                        invalidar_cache("Avaliacao_Inicial")
                        st.session_state["_horario_ultimo_autosave"] = datetime.now().strftime("%H:%M:%S")
                        toast("Avaliação Inicial sincronizada com sucesso!", "success")
                    except Exception as e:
                        toast(f"Erro ao comunicar com a base de dados: {e}", "error")

    with c_btn_pdf:
        try:
            bytes_pdf_aval = gerar_pdf_somente_avaliacao(dados_avaliacao)
            nome_pac_limpo = str(st.session_state.get("paciente", "paciente")).replace(" ", "_")
            st.download_button(
                label="📄 EXPORTAR AVALIAÇÃO EM PDF",
                data=bytes_pdf_aval,
                file_name=f"Avaliacao_GENUA_{nome_pac_limpo}_{data_aval_input.strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                type="secondary",
                width="stretch",
            )
        except Exception as e:
            st.error(f"Erro ao preparar PDF da avaliação: {e}")
