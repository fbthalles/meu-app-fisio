"""GENUA | Módulo 1: Avaliação Inicial (O Marco Zero) — Estilo Apple HIG."""
import streamlit as st
from datetime import datetime
from PIL import Image, ImageDraw

try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    _HAS_IMAGE_COORDS = True
except (ImportError, Exception):
    _HAS_IMAGE_COORDS = False

from config import CORES_GENUA, titulo, secao, toast
from firebase_client import db, invalidar_cache


def render():
    # Cabeçalho limpo estilo Apple Health
    st.markdown(f"""
        <div style='margin-bottom: 20px;'>
            <h2 style='margin-bottom: 4px;'>🔎 Avaliação Inicial (Marco Zero)</h2>
            <p style='color: {CORES_GENUA['texto_suave']}; font-size: 0.94rem; margin: 0;'>
                Primeira Consulta · Estabelecimento de Baseline Clínica Bilateral, Triagem de Bandeiras, Força, Metas (PSFS) e PROMs.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --- MOTOR DE CONSULTA E EDIÇÃO ---
    st.session_state.setdefault('doc_id_avaliacao', None)
    st.session_state.setdefault('dados_antigos', None)

    avaliacoes_existentes = []
    if 'paciente' in st.session_state and st.session_state.paciente:
        try:
            docs = db.collection("Avaliacao_Inicial").where("Paciente", "==", st.session_state.paciente).stream()
            avaliacoes_existentes = [{"id": d.id, "data": d.to_dict()} for d in docs]
            avaliacoes_existentes.sort(
                key=lambda x: datetime.strptime(x["data"].get("Data_Avaliacao", "01/01/2000"), "%d/%m/%Y"),
                reverse=True
            )
        except Exception:
            avaliacoes_existentes = []

    # ============================================================
    # 1. CARD SELETOR DE MODO (Nova Avaliação x Editar Existente)
    # ============================================================
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
                    help="Selecione 'Nova Avaliação' para criar do zero ou escolha uma existente para editar."
                )
            else:
                st.info("ℹ️ Este paciente ainda não possui Avaliação Inicial. Preencha as abas abaixo para registrar o baseline.")
                escolha = "➕ Nova Avaliação"

        with col_modo2:
            if avaliacoes_existentes and escolha != "➕ Nova Avaliação":
                st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Excluir Avaliação", type="secondary", width="stretch"):
                    st.session_state['confirmar_exclusao_aval'] = True

        # Confirmação de exclusão
        if st.session_state.get('confirmar_exclusao_aval'):
            st.warning("⚠️ Tem certeza? Esta ação removerá a avaliação permanentemente.")
            cc1, cc2, _ = st.columns([1, 1, 2])
            with cc1:
                if st.button("✅ Sim, excluir", type="primary", width="stretch"):
                    try:
                        idx = opcoes.index(escolha) - 1
                        doc_id = avaliacoes_existentes[idx]["id"]
                        db.collection("Avaliacao_Inicial").document(doc_id).delete()
                        invalidar_cache("Avaliacao_Inicial")
                        st.session_state['confirmar_exclusao_aval'] = False
                        toast("Avaliação excluída com sucesso.", "success")
                        st.rerun()
                    except Exception as e:
                        toast(f"Erro ao excluir: {e}", "error")
            with cc2:
                if st.button("❌ Cancelar", type="secondary", width="stretch"):
                    st.session_state['confirmar_exclusao_aval'] = False
                    st.rerun()

    # Define modo de operação
    if escolha == "➕ Nova Avaliação":
        st.session_state.doc_id_avaliacao = None
        st.session_state.dados_antigos = None
    else:
        idx = opcoes.index(escolha) - 1
        st.session_state.dados_antigos = avaliacoes_existentes[idx]["data"]
        st.session_state.doc_id_avaliacao = avaliacoes_existentes[idx]["id"]

    # --- HELPERS DE AUTO-PREENCHIMENTO E RETROCOMPATIBILIDADE ---
    dados = st.session_state.get('dados_antigos') or {}

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
        lista_bruta = val if isinstance(val, list) else [v.strip() for v in str(val).split(',')]
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

    # Sincroniza pontos do mapa da dor ao carregar avaliação existente
    doc_atual_key = st.session_state.get("doc_id_avaliacao") or "nova"
    if st.session_state.get("_ultimo_doc_mapa") != doc_atual_key:
        pontos_salvos = dados.get("Pontos_Mapa_Dor", [])
        st.session_state.pontos_dor = pontos_salvos if isinstance(pontos_salvos, list) else []
        st.session_state.last_click = None
        st.session_state["_ultimo_doc_mapa"] = doc_atual_key

    # ============================================================
    # 2. NAVEGAÇÃO EM ABAS (Segmented Control iOS)
    # ============================================================
    t_anamnese, t_dor, t_flags, t_fisico, t_funcional, t_exames, t_quest = st.tabs([
        "🗣️ Anamnese", "💥 Dor", "🚩 Bandeiras", "📐 Físico", "🏃 Funcional", "🩻 Exames", "📋 Questionários"
    ])

    # --- ABA 1: ANAMNESE ---
    with t_anamnese:
        with st.container(border=True):
            secao(
                "🗣️ Histórico Clínico, Lateralidade e Contexto",
                "Mapeamento do membro acometido, queixa principal, comportamento mecânico dos sintomas e histórico prévio."
            )
            c_qp, c_lado = st.columns([2.2, 1])
            with c_qp:
                qp = st.text_input(
                    "Queixa Principal (QP) *",
                    value=dados.get("QP", ""),
                    placeholder="O que o paciente deixou de fazer devido à dor?"
                )
            with c_lado:
                op_lado = ["Direito", "Esquerdo", "Bilateral (Dir > Esq)", "Bilateral (Esq > Dir)", "Bilateral (Simétrico)"]
                lado_acometido = st.selectbox(
                    "🦵 Lado Acometido Principal *",
                    op_lado,
                    index=get_idx(op_lado, "Lado_Acometido"),
                    help="Essencial para o cálculo determinístico do Limb Symmetry Index (LSI) no motor de IA Clínica."
                )

            hma = st.text_area(
                "História da Moléstia Atual (HMA) *",
                value=dados.get("HMA", ""),
                placeholder="Descrição detalhada do mecanismo de lesão, início e evolução do quadro...",
                height=110
            )
            sinais_sintomas = st.text_input(
                "Sinais e Sintomas Associados",
                value=dados.get("Sinais_Sintomas", ""),
                placeholder="Ex: Dor na interlinha medial, crepitação, falseio, bloqueio..."
            )

            c_an1, c_an2 = st.columns(2)
            with c_an1:
                fat_alivio = st.text_input(
                    "🟢 Fatores de Alívio",
                    value=dados.get("Fatores_Alivio", ""),
                    placeholder="Ex: Repouso, crioterapia, extensão ativa..."
                )
            with c_an2:
                fat_piora = st.text_input(
                    "🔴 Fatores de Piora",
                    value=dados.get("Fatores_Piora", ""),
                    placeholder="Ex: Descer escadas, agachamento profundo, corrida..."
                )

            trat_previos = st.text_area(
                "Tratamentos e Intervenções Anteriores",
                value=dados.get("Tratamentos_Previos", ""),
                placeholder="Cirurgias prévias, infiltrações, fisioterapia anterior...",
                height=85
            )

    # --- ABA 2: DOR E MAPA ANATÔMICO ---
    with t_dor:
        with st.container(border=True):
            secao(
                "💥 Classificação Neurofisiológica e Origem",
                "Defina o mecanismo predominante de dor (IASP) e o início dos sintomas."
            )
            c_dor1, c_dor2 = st.columns(2)
            op_class = [
                "Nociceptiva (Mecânica/Inflamatória)",
                "Neuropática (Irradiação/Queimação)",
                "Nociplástica (Sensibilização Central)",
                "Não Aplicável"
            ]
            with c_dor1:
                class_dor = st.selectbox("Classificação da Dor *", op_class, index=get_idx(op_class, "Class_Dor"))

            op_origem = ["Traumática", "Insidiosa / Sobrecarga", "Pós-operatória", "Degenerativa", "Não Aplicável"]
            with c_dor2:
                origem_dor = st.selectbox("Origem / Mecanismo *", op_origem, index=get_idx(op_origem, "Origem_Dor"))

        with st.container(border=True):
            secao(
                "🎯 Mapa Anatômico Interativo da Dor",
                "Toque ou clique diretamente sobre a imagem do joelho para registrar os pontos álgicos."
            )

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
                            px, py = ponto.get('x', 0), ponto.get('y', 0)
                        elif isinstance(ponto, (tuple, list)) and len(ponto) >= 2:
                            px, py = ponto[0], ponto[1]
                        else:
                            continue
                        raio = 7
                        draw.ellipse((px - raio, py - raio, px + raio, py + raio), fill="#FF3B30", outline="#FFFFFF", width=2)

                    if _HAS_IMAGE_COORDS:
                        value = streamlit_image_coordinates(img_base, key=f"joelho_map_{st.session_state.map_key}")
                    else:
                        st.image(img_base, caption="Mapa de Dor (interação requer streamlit-image-coordinates)")
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
                        default=get_list(op_zonas, "Zonas_Dor_Dir") or (get_list(op_zonas, "Zonas_Dor") if "Direito" in lado_acometido or "Bilateral" in lado_acometido else [])
                    )
                with c_z2:
                    zonas_dor_e = st.multiselect(
                        "📍 Zonas de Dor — Joelho ESQUERDO",
                        op_zonas,
                        default=get_list(op_zonas, "Zonas_Dor_Esq") or (get_list(op_zonas, "Zonas_Dor") if "Esquerdo" in lado_acometido or "Bilateral" in lado_acometido else [])
                    )

                mapa_dor = st.text_area(
                    "📝 Notas Detalhadas do Mapa da Dor",
                    value=dados.get("Mapa_Dor", ""),
                    placeholder="Ex: Dor puntiforme no polo inferior da patela direita ao agachar...",
                    height=115
                )
                if st.button("🗑️ Limpar Marcadores do Mapa", type="secondary"):
                    st.session_state.pontos_dor = []
                    st.session_state.last_click = None
                    st.session_state.map_key += 1
                    st.rerun()

    # --- ABA 3: BANDEIRAS (TRIAGEM BIOPSICOSSOCIAL) ---
    with t_flags:
        with st.container(border=True):
            secao(
                "🚩 Sistema de Triagem por Bandeiras (PBE)",
                "Rastreio de sinais de alerta clínico (Red Flags) e moduladores psicossociais (Yellow/Blue Flags)."
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
                default=get_list(op_red, "Red_Flags")
            )

            op_yellow = [
                "Nenhum", "Cinesiofobia (Medo de movimento)", "Catastrofização",
                "Baixa auto-eficácia", "Sintomas depressivos / Ansiedade",
                "Expectativas irreais de recuperação"
            ]
            yellow_cog = st.multiselect(
                "🟡 Yellow Flags (Fatores Cognitivo-Emocionais) *",
                op_yellow,
                default=get_list(op_yellow, "Yellow_Cog")
            )

            c_fl1, c_fl2 = st.columns(2)
            op_sono = ["Normal/Restaurador", "Irregular", "Ruim (Insônia/Acorda com dor)"]
            with c_fl1:
                qualidade_sono = st.selectbox("🌙 Qualidade do Sono *", op_sono, index=get_idx(op_sono, "Sono"))

            op_sociais = [
                "Nenhum", "Trabalho braçal/Carga pesada", "Afastado pelo INSS",
                "Sedentarismo", "Litígio/Processo judicial", "Falta de suporte familiar"
            ]
            with c_fl2:
                fat_sociais = st.multiselect(
                    "🔵 Fatores Contextuais / Ocupacionais (Blue/Black Flags) *",
                    op_sociais,
                    default=get_list(op_sociais, "Fatores_Sociais")
                )

            op_comorb = [
                "Nenhuma", "Hipertensão", "Diabetes", "Obesidade (IMC > 30)",
                "Cardiopatia", "Doença Autoimune", "Osteoporose", "Tabagismo", "Distúrbio Vascular"
            ]
            comorbidades = st.multiselect(
                "🩺 Comorbidades Associadas *",
                op_comorb,
                default=get_list(op_comorb, "Comorbidades")
            )

    # --- ABA 4: EXAME FÍSICO E TESTES ESPECIAIS (SEPARADOS ENTRE DIREITO E ESQUERDO) ---
    with t_fisico:
        with st.container(border=True):
            secao(
                "👁️ Inspeção, Trofismo e Palpação (Comparativo Bilateral: Direito × Esquerdo)",
                "Avaliação morfológica, efusão articular, perimetria de coxa e sensibilidade à palpação separados por dimídio."
            )

            op_mar = ["Normal", "Antálgica", "Claudicante", "Marcha em Flexo de Joelho", "Uso de dispositivo auxiliar (Muleta/Bengala)"]
            marcha = st.selectbox("🚶 Padrão Global de Marcha", op_mar, index=get_idx(op_mar, "Marcha"))

            st.markdown("<hr style='margin: 14px 0;'>", unsafe_allow_html=True)

            op_der = ["Ausente", "Vestígio (Onda +)", "Leve (1+)", "Moderado (2+)", "Grave / Tenso (3+)"]
            op_ali = ["Normal", "Valgo", "Varo", "Recurvatum", "Flexo"]
            op_trof = ["Normal", "Hipotrofia Leve", "Hipotrofia Moderada", "Hipotrofia Severa"]
            op_palp = ["Nenhuma / Indolor", "Anterior (Patelar/Tendão)", "Medial (Interlinha/Pata de Ganso)", "Lateral (Interlinha/Trato Iliotibial)", "Posterior (Poplítea)"]
            op_godet = ["Negativo", "Positivo"]
            op_temp = ["Normal", "Aumentada (Calor local)", "Diminuída"]

            col_fis_d, col_fis_e = st.columns(2, gap="large")

            # --- COLUNA MEMBRO DIREITO ---
            with col_fis_d:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-bottom: 8px;'>🦵 Membro Inferior DIREITO</h4>", unsafe_allow_html=True)
                derrame_d = st.selectbox(
                    "Derrame Articular — Direito (Tecla/Onda)",
                    op_der, index=get_idx(op_der, "Derrame_Dir", "Derrame"), key="der_d"
                )
                alinhamento_d = st.selectbox(
                    "Alinhamento Estático — Direito",
                    op_ali, index=get_idx(op_ali, "Alinhamento_Dir", "Alinhamento"), key="ali_d"
                )
                trofismo_d = st.selectbox(
                    "Trofismo Muscular — Perna Direita",
                    op_trof, index=get_idx(op_trof, "Trofismo_Dir", "Trofismo"), key="trof_d"
                )
                perimetria_d = st.number_input(
                    "Perimetria Coxa Direita (cm — 10 cm supra-patelar)",
                    min_value=0.0, max_value=100.0, step=0.5,
                    value=float(dados.get("Perimetria_Dir_cm", 0.0) or 0.0), key="perim_d"
                )
                palpacao_d = st.multiselect(
                    "Estruturas Dolorosas à Palpação — Direito",
                    op_palp, default=get_list(op_palp, "Palpacao_Dir") or get_list(op_palp, "Palpacao"), key="palp_d"
                )
                c_gd1, c_gd2 = st.columns(2)
                with c_gd1:
                    godet_d = st.radio("Sinal de Godet (Dir)", op_godet, index=get_idx(op_godet, "Godet_Dir", "Godet"), key="god_d")
                with c_gd2:
                    temp_d = st.radio("Temperatura (Dir)", op_temp, index=get_idx(op_temp, "Temperatura_Dir", "Temperatura"), key="tmp_d")

            # --- COLUNA MEMBRO ESQUERDO ---
            with col_fis_e:
                st.markdown(f"<h4 style='color: {CORES_GENUA['secundaria']}; margin-bottom: 8px;'>🦵 Membro Inferior ESQUERDO</h4>", unsafe_allow_html=True)
                derrame_e = st.selectbox(
                    "Derrame Articular — Esquerdo (Tecla/Onda)",
                    op_der, index=get_idx(op_der, "Derrame_Esq", "Derrame"), key="der_e"
                )
                alinhamento_e = st.selectbox(
                    "Alinhamento Estático — Esquerdo",
                    op_ali, index=get_idx(op_ali, "Alinhamento_Esq", "Alinhamento"), key="ali_e"
                )
                trofismo_e = st.selectbox(
                    "Trofismo Muscular — Perna Esquerda",
                    op_trof, index=get_idx(op_trof, "Trofismo_Esq", "Trofismo"), key="trof_e"
                )
                perimetria_e = st.number_input(
                    "Perimetria Coxa Esquerda (cm — 10 cm supra-patelar)",
                    min_value=0.0, max_value=100.0, step=0.5,
                    value=float(dados.get("Perimetria_Esq_cm", 0.0) or 0.0), key="perim_e"
                )
                palpacao_e = st.multiselect(
                    "Estruturas Dolorosas à Palpação — Esquerdo",
                    op_palp, default=get_list(op_palp, "Palpacao_Esq") or get_list(op_palp, "Palpacao"), key="palp_e"
                )
                c_ge1, c_ge2 = st.columns(2)
                with c_ge1:
                    godet_e = st.radio("Sinal de Godet (Esq)", op_godet, index=get_idx(op_godet, "Godet_Esq", "Godet"), key="god_e")
                with c_ge2:
                    temp_e = st.radio("Temperatura (Esq)", op_temp, index=get_idx(op_temp, "Temperatura_Esq", "Temperatura"), key="tmp_e")

            # Cálculo automático de assimetria de perimetria de coxa
            if perimetria_d > 0 and perimetria_e > 0:
                diff_perim = perimetria_d - perimetria_e
                if abs(diff_perim) >= 1.5:
                    menor_lado = "Direita" if diff_perim < 0 else "Esquerda"
                    st.warning(
                        f"⚠️ **Assimetria Trofismo/Perimetria Detectada:** Diferença de **{abs(diff_perim):.1f} cm** "
                        f"(Hipotrofia na coxa **{menor_lado}** — relevância clínica ≥ 1,5 cm)."
                    )
                else:
                    st.caption(f"✅ **Perimetria de Coxa:** Diferença fisiológica ({abs(diff_perim):.1f} cm < 1,5 cm).")

            st.markdown("<hr style='margin: 14px 0;'>", unsafe_allow_html=True)
            c_pele, c_perim_obs = st.columns(2)
            op_pele = ["Nenhuma", "Equimose", "Hematoma", "Cicatrizes Cirúrgicas", "Aderência Cicatricial", "Fístulas"]
            with c_pele:
                pele = st.multiselect("Alterações Cutâneas / Cicatriciais", op_pele, default=get_list(op_pele, "Pele"))
            with c_perim_obs:
                perimetria_obs = st.text_input(
                    "Notas Adicionais de Perimetria / Edema (ex: 15 cm supra ou linha articular)",
                    value=dados.get("Perimetria", ""),
                    placeholder="Ex: -2,5 cm a 15 cm da borda superior da patela D"
                )

        # Card 2 da Aba Físico: Testes Especiais Bilaterais
        with st.container(border=True):
            secao(
                "🧪 Testes Especiais Ortopédicos (Separados por Joelho: Direito × Esquerdo)",
                "Clusters diagnósticos ligamentares, meniscais e femoropatelares/tendíneos."
            )
            op_lig = ["Nenhum", "Lachman", "Gaveta Anterior", "Gaveta Posterior", "Estresse Valgo", "Estresse Varo", "Pivot Shift", "Dial Test"]
            op_men = ["Nenhum", "Ege", "Thessaly (20°)", "McMurray", "Apley", "Sensibilidade Interlinha (JLT)"]
            op_pat = [
                "Nenhum", "Step Up Doloroso", "Step Down Doloroso", "Extensão CCA Dolorosa",
                "Sinal de Clarke", "Apreensão Patelar",
                "Decline Squat (Tendinopatia)", "Teste de Noble (Trato Iliotibial)"
            ]

            c_te_d, c_te_e = st.columns(2, gap="large")
            with c_te_d:
                st.markdown(f"**🦵 Joelho DIREITO (Marcar Positivos)**")
                t_lig_d = st.multiselect("🔗 Ligamentares (Direito)", op_lig, default=get_list(op_lig, "Testes_Ligamentares_Dir") or get_list(op_lig, "Testes_Ligamentares"), key="t_lig_d")
                t_men_d = st.multiselect("🌙 Meniscais (Direito)", op_men, default=get_list(op_men, "Testes_Meniscais_Dir") or get_list(op_men, "Testes_Meniscais"), key="t_men_d")
                t_pat_d = st.multiselect("🎯 Femoropatelares / Tendíneos (Direito)", op_pat, default=get_list(op_pat, "Testes_Femoropatelar_Dir") or get_list(op_pat, "Testes_Femoropatelar"), key="t_pat_d")

            with c_te_e:
                st.markdown(f"**🦵 Joelho ESQUERDO (Marcar Positivos)**")
                t_lig_e = st.multiselect("🔗 Ligamentares (Esquerdo)", op_lig, default=get_list(op_lig, "Testes_Ligamentares_Esq"), key="t_lig_e")
                t_men_e = st.multiselect("🌙 Meniscais (Esquerdo)", op_men, default=get_list(op_men, "Testes_Meniscais_Esq"), key="t_men_e")
                t_pat_e = st.multiselect("🎯 Femoropatelares / Tendíneos (Esquerdo)", op_pat, default=get_list(op_pat, "Testes_Femoropatelar_Esq"), key="t_pat_e")

    # --- ABA 5: AVALIAÇÃO FUNCIONAL, OBJETIVO DO PACIENTE (PSFS/SANE), DINAMOMETRIA E GONIOMETRIA ---
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

        def get_val_cm(chave_db, prefix):
            try:
                val = dados.get(chave_db, "")
                if not val:
                    return "3 - Normal"
                parts = val.split(" | ")
                for p in parts:
                    if p.startswith(prefix + ":"):
                        return p.split(":")[1]
            except (ValueError, TypeError, AttributeError):
                pass
            return "3 - Normal"

        # Card 0 (NOVO PBE): Objetivo do Paciente & Distância da Meta (PSFS + SANE)
        with st.container(border=True):
            secao(
                "🎯 Objetivo Funcional do Paciente & Distância da Meta (PSFS + SANE — PBE)",
                "Patient-Specific Functional Scale (Stratford et al., 1995 — MCID: 2,0 pts) & Single Assessment Numeric Evaluation (Shelbourne et al., 2009)."
            )
            obj_paciente = st.text_input(
                "🏆 Qual é o principal objetivo que o paciente veio buscar na fisioterapia?",
                value=dados.get("Objetivo_Paciente", ""),
                placeholder="Ex: Voltar a correr 10 km sem dor, jogar futebol no fim de semana, descer escadas sem travar..."
            )
            c_psfs1, c_psfs2 = st.columns(2, gap="large")
            with c_psfs1:
                psfs_baseline = st.slider(
                    "📊 Escala Funcional Específica (PSFS: 0 = Incapaz | 10 = Nível Pré-Lesão)",
                    min_value=0, max_value=10,
                    value=int(dados.get("PSFS_Baseline", 3) if dados.get("PSFS_Baseline") is not None else 3),
                    help="Quão capaz o paciente se sente HOJE de realizar essa atividade específica? (Variacão ≥ 2 pontos = melhora clinicamente relevante)."
                )
            with c_psfs2:
                sane_baseline = st.slider(
                    "📏 Quão perto do objetivo final ele sente que está hoje? (SANE: 0% a 100%)",
                    min_value=0, max_value=100, step=5,
                    value=int(dados.get("SANE_Baseline_Pct", 30) if dados.get("SANE_Baseline_Pct") is not None else 30),
                    help="0% = No ponto zero / Muito longe da meta | 100% = Objetivo 100% atingido."
                )

            distancia_meta = 100 - sane_baseline
            st.info(
                f"🧭 **Status da Meta Baseline:** Capacidade atual de **{sane_baseline}%** (PSFS: **{psfs_baseline}/10**). "
                f"Faltam **{distancia_meta}%** de evolução percebida para atingir o objetivo principal."
            )

        # Card 1: Força Muscular e Dinamometria com Cálculo de LSI em Tempo Real
        with st.container(border=True):
            secao(
                "💪 Força Muscular (Oxford) e Dinamometria Isométrica (kgf)",
                "O sistema calcula automaticamente o Índice de Simetria (LSI %) ao preencher os valores bilaterais."
            )
            st.caption("1. Força Manual Qualitativa (Escala de Oxford 0 a 5)")
            c_fg1, c_fg2, c_fg3, c_fg4 = st.columns(4)
            fg_ext_d = c_fg1.number_input("Extensão (Dir) [0-5]", min_value=0, max_value=5, value=get_val_str("Forca_Geral_Dir", "Ext", 5))
            fg_flex_d = c_fg2.number_input("Flexão (Dir) [0-5]", min_value=0, max_value=5, value=get_val_str("Forca_Geral_Dir", "Flex", 5))
            fg_abd_d = c_fg3.number_input("Abdução (Dir) [0-5]", min_value=0, max_value=5, value=get_val_str("Forca_Geral_Dir", "Abd", 5))
            fg_add_d = c_fg4.number_input("Adução (Dir) [0-5]", min_value=0, max_value=5, value=get_val_str("Forca_Geral_Dir", "Add", 5))

            c_fg5, c_fg6, c_fg7, c_fg8 = st.columns(4)
            fg_ext_e = c_fg5.number_input("Extensão (Esq) [0-5]", min_value=0, max_value=5, value=get_val_str("Forca_Geral_Esq", "Ext", 5))
            fg_flex_e = c_fg6.number_input("Flexão (Esq) [0-5]", min_value=0, max_value=5, value=get_val_str("Forca_Geral_Esq", "Flex", 5))
            fg_abd_e = c_fg7.number_input("Abdução (Esq) [0-5]", min_value=0, max_value=5, value=get_val_str("Forca_Geral_Esq", "Abd", 5))
            fg_add_e = c_fg8.number_input("Adução (Esq) [0-5]", min_value=0, max_value=5, value=get_val_str("Forca_Geral_Esq", "Add", 5))

            st.markdown("<hr style='margin: 16px 0;'>", unsafe_allow_html=True)
            st.caption("2. Dinamometria Quantitativa (Handheld Dynamometer — kgf)")
            c_din1, c_din2, c_din3, c_din4 = st.columns(4)
            din_ext_d = c_din1.number_input("Extensão Dir (kg)", min_value=0.0, step=1.0, value=get_val_str("Dinamometria_Dir", "Ext", 0.0, float))
            din_flex_d = c_din2.number_input("Flexão Dir (kg)", min_value=0.0, step=1.0, value=get_val_str("Dinamometria_Dir", "Flex", 0.0, float))
            din_abd_d = c_din3.number_input("Abdução Dir (kg)", min_value=0.0, step=1.0, value=get_val_str("Dinamometria_Dir", "Abd", 0.0, float))
            din_add_d = c_din4.number_input("Adução Dir (kg)", min_value=0.0, step=1.0, value=get_val_str("Dinamometria_Dir", "Add", 0.0, float))

            c_din5, c_din6, c_din7, c_din8 = st.columns(4)
            din_ext_e = c_din5.number_input("Extensão Esq (kg)", min_value=0.0, step=1.0, value=get_val_str("Dinamometria_Esq", "Ext", 0.0, float))
            din_flex_e = c_din6.number_input("Flexão Esq (kg)", min_value=0.0, step=1.0, value=get_val_str("Dinamometria_Esq", "Flex", 0.0, float))
            din_abd_e = c_din7.number_input("Abdução Esq (kg)", min_value=0.0, step=1.0, value=get_val_str("Dinamometria_Esq", "Abd", 0.0, float))
            din_add_e = c_din8.number_input("Adução Esq (kg)", min_value=0.0, step=1.0, value=get_val_str("Dinamometria_Esq", "Add", 0.0, float))

            # Análise instantânea de Simetria (LSI %)
            pares_din = [
                ("Extensão (Quadríceps)", din_ext_d, din_ext_e),
                ("Flexão (Isquiotibiais)", din_flex_d, din_flex_e),
                ("Abdução (Glúteo Médio)", din_abd_d, din_abd_e),
                ("Adução (Adutores)", din_add_d, din_add_e),
            ]
            ativos_din = [(nome, d, e) for nome, d, e in pares_din if d > 0 or e > 0]
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

                    lsi_g = (lesado / saudavel * 100.0) if saudavel > 0 else 0.0
                    diff_kg = abs(val_d - val_e)
                    lado_forte = "Dir +" if val_d > val_e else "Esq +" if val_e > val_d else "Simétrico"
                    with cols_lsi[idx_l]:
                        st.metric(
                            label=f"LSI {nome_g.split()[0]}",
                            value=f"{lsi_g:.0f}%",
                            delta=f"Δ {diff_kg:.1f}kg ({lado_forte})",
                            delta_color="normal" if lsi_g >= 90 else "inverse"
                        )

        # Card 2: Mobilidade Articular (Goniometria e Lunge Test)
        with st.container(border=True):
            secao("📐 Mobilidade Articular (Goniometria e Lunge Test)", "Amplitude de movimento ativa/passiva de joelho e dorsiflexão em cadeia fechada.")
            c_flex1, c_flex2, c_ext1, c_ext2 = st.columns(4)
            adm_flex_d = c_flex1.number_input(
                "Flexão (Dir) °", min_value=0.0, max_value=160.0, step=1.0,
                value=get_val_str("ADM_Joelho_Flexao", "Dir", 0.0, float), key="adm_flex_d"
            )
            adm_flex_e = c_flex2.number_input(
                "Flexão (Esq) °", min_value=0.0, max_value=160.0, step=1.0,
                value=get_val_str("ADM_Joelho_Flexao", "Esq", 0.0, float), key="adm_flex_e"
            )
            adm_ext_d = c_ext1.number_input(
                "Extensão (Dir) °", min_value=-15.0, max_value=30.0, step=1.0,
                value=get_val_str("ADM_Joelho_Extensao", "Dir", 0.0, float),
                help="0° = extensão neutra. Positivos = déficit (flexo); Negativos = hiperextensão.", key="adm_ext_d"
            )
            adm_ext_e = c_ext2.number_input(
                "Extensão (Esq) °", min_value=-15.0, max_value=30.0, step=1.0,
                value=get_val_str("ADM_Joelho_Extensao", "Esq", 0.0, float),
                help="0° = extensão neutra. Positivos = déficit (flexo); Negativos = hiperextensão.", key="adm_ext_e"
            )

            if adm_flex_d > 0 and adm_flex_e > 0:
                diff_flex = abs(adm_flex_d - adm_flex_e)
                if diff_flex >= 10:
                    st.warning(f"⚠️ **Assimetria de Flexão:** Diferença de {diff_flex:.1f}° entre os joelhos (relevância clínica ≥ 10°).")
                elif diff_flex == 0:
                    st.caption("✅ **Flexão de Joelho:** Simetria bilateral completa.")

            if (adm_ext_d >= 5) or (adm_ext_e >= 5):
                st.warning("⚠️ **Atenção:** Déficit de extensão terminal ≥ 5° aumenta sobrecarga femoropatelar e altera a cinemática da marcha.")

            st.markdown("<hr style='margin: 16px 0;'>", unsafe_allow_html=True)
            c_lunge1, c_lunge2 = st.columns(2)
            lunge_d = c_lunge1.number_input(
                "Lunge Test — Tornozelo Direito (cm)", min_value=0.0, step=0.5,
                value=get_val_str("Lunge_Test", "Dir", 0.0, float), key="lunge_d"
            )
            lunge_e = c_lunge2.number_input(
                "Lunge Test — Tornozelo Esquerdo (cm)", min_value=0.0, step=0.5,
                value=get_val_str("Lunge_Test", "Esq", 0.0, float), key="lunge_e"
            )

            if lunge_d > 0 or lunge_e > 0:
                diff_lunge = lunge_d - lunge_e
                if abs(diff_lunge) >= 1.5:
                    lado_menor = "Esquerdo" if diff_lunge > 0 else "Direito"
                    st.info(f"📊 **Assimetria no Lunge Test:** Diferença de {abs(diff_lunge):.1f} cm (restrição maior à dorsiflexão no lado **{lado_menor}**).")

        # Card 3: Controle Motor, Flexibilidade Bilateral e Alvos do Check-in
        with st.container(border=True):
            secao(
                "⚙️ Controle Motor, Flexibilidade Bilateral e Alvos de Check-in",
                "Escala qualitativa de movimento (3 = Normal | 2 = Regular | 1 = Ruim | 0 = Incapaz)."
            )
            opcoes_cm = ["3 - Normal", "2 - Regular", "1 - Ruim", "0 - Incapaz"]

            def get_cm_idx(chave_db, prefix):
                val = get_val_cm(chave_db, prefix)
                return opcoes_cm.index(val) if val in opcoes_cm else 0

            cm1, cm2, cm3 = st.columns(3)
            with cm1:
                st.caption("PADRÕES GLOBAIS")
                cm_marcha = st.selectbox("Marcha", opcoes_cm, index=get_cm_idx("CM_Globais", "Marcha"))
                cm_corrida = st.selectbox("Corrida", opcoes_cm, index=get_cm_idx("CM_Globais", "Corrida"))
                cm_salto = st.selectbox("Salto Bipodal", opcoes_cm, index=get_cm_idx("CM_Globais", "Salto"))
                cm_agach_bi = st.selectbox("Agachamento Bipodal", opcoes_cm, index=get_cm_idx("CM_Globais", "Agach_Bi"))

            with cm2:
                st.caption("MEMBRO DIREITO")
                cm_agach_uni_d = st.selectbox("Agachamento Uni (D)", opcoes_cm, index=get_cm_idx("CM_Membro_Dir", "Agach"))
                cm_step_down_d = st.selectbox("Step Down (D)", opcoes_cm, index=get_cm_idx("CM_Membro_Dir", "StepDown"))
                cm_step_up_d = st.selectbox("Step Up (D)", opcoes_cm, index=get_cm_idx("CM_Membro_Dir", "StepUp"))
                cm_afundo_d = st.selectbox("Afundo (D)", opcoes_cm, index=get_cm_idx("CM_Membro_Dir", "Afundo"))
                cm_eq_uni_d = st.selectbox("Equilíbrio Uni (D)", opcoes_cm, index=get_cm_idx("CM_Membro_Dir", "Eq"))

            with cm3:
                st.caption("MEMBRO ESQUERDO")
                cm_agach_uni_e = st.selectbox("Agachamento Uni (E)", opcoes_cm, index=get_cm_idx("CM_Membro_Esq", "Agach"))
                cm_step_down_e = st.selectbox("Step Down (E)", opcoes_cm, index=get_cm_idx("CM_Membro_Esq", "StepDown"))
                cm_step_up_e = st.selectbox("Step Up (E)", opcoes_cm, index=get_cm_idx("CM_Membro_Esq", "StepUp"))
                cm_afundo_e = st.selectbox("Afundo (E)", opcoes_cm, index=get_cm_idx("CM_Membro_Esq", "Afundo"))
                cm_eq_uni_e = st.selectbox("Equilíbrio Uni (E)", opcoes_cm, index=get_cm_idx("CM_Membro_Esq", "Eq"))

            st.markdown("<hr style='margin: 16px 0;'>", unsafe_allow_html=True)
            op_flex = [
                "Nenhuma", "Thomas (+) - Iliopsoas", "Thomas (+) - Reto Femoral",
                "Ely (+) - Reto Femoral", "Ober (+) - Trato Iliotibial", " Encurtamento Isquiotibiais ( Ângulo Poplíteo)"
            ]
            c_flx_d, c_flx_e = st.columns(2)
            with c_flx_d:
                flexibilidade_d = st.multiselect(
                    "🧘 Flexibilidade / Retrações — Membro DIREITO",
                    op_flex, default=get_list(op_flex, "Flexibilidade_Dir") or get_list(op_flex, "Flexibilidade"), key="flx_d"
                )
            with c_flx_e:
                flexibilidade_e = st.multiselect(
                    "🧘 Flexibilidade / Retrações — Membro ESQUERDO",
                    op_flex, default=get_list(op_flex, "Flexibilidade_Esq") or get_list(op_flex, "Flexibilidade"), key="flx_e"
                )

            st.markdown("<hr style='margin: 18px 0;'>", unsafe_allow_html=True)
            secao(
                "🎯 Alvos Funcionais para o Check-in Diário",
                "Os movimentos selecionados abaixo aparecerão automaticamente como pílulas de 1 toque no Check-in Diário deste paciente."
            )
            lista_testes_disp = [
                "Agachamento Bipodal", "Agachamento Unipodal (D)", "Agachamento Unipodal (E)",
                "Step Down (D)", "Step Down (E)", "Lunge / Afundo", "Salto (Hop Test)", "Corrida", "Marcha"
            ]
            def_alvos = get_list("Testes_Alvo")
            # Mantém compatibilidade com nomes antigos se já salvos
            for t_antigo in def_alvos:
                if t_antigo not in lista_testes_disp:
                    lista_testes_disp.append(t_antigo)
            if not def_alvos:
                def_alvos = ["Agachamento Bipodal", "Step Down (D)" if "Direito" in lado_acometido else "Step Down (E)"]
            testes_alvo = st.multiselect("Testes Funcionais Diários:", lista_testes_disp, default=def_alvos)

    # --- ABA 6: EXAMES COMPLEMENTARES ---
    with t_exames:
        with st.container(border=True):
            secao("🩻 Exames Complementares e Imagem", "Registre os exames trazidos pelo paciente e os principais achados radiológicos.")
            op_exames = [
                "Nenhum", "Raio-X", "Ressonância Magnética (RM)",
                "Tomografia Computadorizada (TC)", "Ultrassonografia (USG)", "Eletroneuromiografia"
            ]
            tipos_exames = st.multiselect("Modalidades de Exame Apresentadas *", op_exames, default=get_list(op_exames, "Exames_Apresentados"))
            laudo_exames = st.text_area(
                "Laudo / Achados Estruturais Relevantes *",
                value=dados.get("Laudo_Exames", "Nenhum"),
                placeholder="Descreva os achados de imagem (especificando lado Direito/Esquerdo) ou mantenha 'Nenhum'.",
                height=140
            )

    # --- ABA 7: QUESTIONÁRIOS (PROMs) ---
    with t_quest:
        with st.container(border=True):
            secao(
                "📋 Questionários de Desfecho Clínico (PROMs)",
                "Expanda os instrumentos aplicáveis ao fenótipo do paciente para calcular o score funcional."
            )

            # 1. LEFS
            with st.expander("📝 LEFS (Escala Funcional da Extremidade Inferior)"):
                opcoes_lefs = {
                    "Incapaz / Extrema Dificuldade": 0, "Muita Dificuldade": 1,
                    "Dificuldade Moderada": 2, "Um Pouco de Dificuldade": 3, "Nenhuma Dificuldade": 4
                }
                perguntas_lefs = [
                    "1. Agachar ou ajoelhar", "2. Andar 2 quarteirões", "3. Subir um lance de escadas",
                    "4. Descer um lance de escadas", "5. Ficar em pé por 1 hora", "6. Correr em terreno plano",
                    "7. Fazer trabalho pesado", "8. Mudança rápida de direção (Corte)"
                ]
                score_lefs = 0
                c_l1, c_l2 = st.columns(2)
                for i, p in enumerate(perguntas_lefs):
                    with (c_l1 if i < 4 else c_l2):
                        score_lefs += opcoes_lefs[st.selectbox(p, list(opcoes_lefs.keys()), key=f"lefs_{i}")]

                pct_lefs = (score_lefs / 32) * 100
                pts_lefs_80 = round((score_lefs / 32) * 80, 1)
                interp_lefs = (
                    "🚨 Função Muito Ruim" if pct_lefs < 30 else
                    "🟡 Função Regular" if pct_lefs < 60 else
                    "🟢 Função Boa" if pct_lefs < 85 else
                    "⭐ Função Excelente"
                )
                st.info(f"📊 **Resultado LEFS:** {pts_lefs_80}/80 pts equivalentes (**{pct_lefs:.1f}%**) — {interp_lefs} *(MCID: 9 pts | Binkley 1999)*")

            # 2. VISA-P
            with st.expander("🎯 VISA-P (Tendinopatia Patelar)"):
                st.caption("0 = Dor máxima / Incapaz · 10 = Sem dor / Perfeito (Máximo: 100 pts).")
                score_visap = 0
                c_v1, c_v2 = st.columns(2)
                with c_v1:
                    score_visap += st.slider("1. Dor ao ficar sentado", 0, 10, 10, key="vp1")
                    score_visap += st.slider("2. Dor ao descer escadas", 0, 10, 10, key="vp2")
                    score_visap += st.slider("3. Dor ao esticar ativamente o joelho", 0, 10, 10, key="vp3")
                    score_visap += st.slider("4. Dor ao fazer um afundo (lunge)", 0, 10, 10, key="vp4")
                with c_v2:
                    score_visap += st.slider("5. Problemas para agachar", 0, 10, 10, key="vp5")
                    score_visap += st.slider("6. Dor durante/após salto ou esporte", 0, 10, 10, key="vp6")
                    p7 = st.selectbox("7. Esporte Atual", ["Não consegue (0 pts)", "Modificado/Menos frequente (4 pts)", "Competindo com dor (7 pts)", "Competindo sem dor (10 pts)"], key="vp7")
                    score_visap += 0 if "0 pts" in p7 else 4 if "4 pts" in p7 else 7 if "7 pts" in p7 else 10
                    p8 = st.selectbox("8. Tempo de dor no esporte", ["Incapaz (0 pts)", "Para aos 15 min (7 pts)", "Dor após o esporte (15 pts)", "Sem dor (30 pts)"], key="vp8")
                    score_visap += 0 if "0 pts" in p8 else 7 if "7 pts" in p8 else 15 if "15 pts" in p8 else 30

                interp_visap = "🚨 Tendinopatia Severa/Aguda" if score_visap < 50 else "🟡 Fase Reativa" if score_visap < 80 else "🟢 Remodelamento/Alta"
                st.info(f"📊 **Resultado VISA-P:** **{score_visap}/100 pontos** — {interp_visap} *(MCID: 13 pts | Hernandez-Sanchez 2014)*")

            # 3. LYSHOLM
            with st.expander("🦵 Escala de Lysholm (Ligamentar e Meniscal)"):
                c_ly1, c_ly2 = st.columns(2)
                score_lysholm = 0
                with c_ly1:
                    score_lysholm += int(st.selectbox("Mancar", ["5 - Nenhum", "3 - Leve ou Periódico", "0 - Grave ou Constante"]).split(" -")[0])
                    score_lysholm += int(st.selectbox("Apoio", ["5 - Nenhum (Não precisa)", "2 - Usa bengala/muleta", "0 - Impossível apoiar"]).split(" -")[0])
                    score_lysholm += int(st.selectbox("Travamento", ["15 - Nenhum", "10 - Sensação de travamento", "6 - Ocasional", "2 - Frequente", "0 - Articulação travada"]).split(" -")[0])
                    score_lysholm += int(st.selectbox("Instabilidade", ["25 - Nunca cede", "20 - Raramente", "15 - Frequente no esporte", "10 - Ocasional em AVDs", "5 - Frequente em AVDs", "0 - A cada passo"]).split(" -")[0])
                with c_ly2:
                    score_lysholm += int(st.selectbox("Dor", ["25 - Nenhuma", "20 - Inconstante ou Leve", "15 - Durante esporte pesado", "10 - Durante esporte leve", "5 - Após andar 2km", "0 - Constante"]).split(" -")[0])
                    score_lysholm += int(st.selectbox("Inchaço", ["10 - Nenhum", "6 - Após esforço intenso", "2 - Após AVDs", "0 - Constante"]).split(" -")[0])
                    score_lysholm += int(st.selectbox("Subir Escadas", ["10 - Sem problemas", "6 - Levemente prejudicado", "2 - Um degrau por vez", "0 - Impossível"]).split(" -")[0])
                    score_lysholm += int(st.selectbox("Agachamento", ["5 - Sem problemas", "4 - Levemente prejudicado", "2 - Não passa de 90 graus", "0 - Impossível"]).split(" -")[0])

                interp_lysholm = "🚨 Ruim (Instabilidade Severa)" if score_lysholm < 65 else "🟡 Regular" if score_lysholm < 84 else "🟢 Bom" if score_lysholm < 95 else "⭐ Excelente"
                st.info(f"📊 **Resultado Lysholm:** **{score_lysholm}/100 pontos** — {interp_lysholm} *(MCID: 10 pts | Briggs 2009)*")

            # 4. WOMAC
            with st.expander("🦴 Índice WOMAC (Osteoartrite)"):
                w_op = {"Nenhuma": 0, "Leve": 1, "Moderada": 2, "Intensa": 3, "Muito Intensa": 4}
                score_womac = 0
                c_w1, c_w2, c_w3 = st.columns(3)
                with c_w1:
                    st.markdown("**Dor (5 itens)**")
                    for p in ["Andar", "Subir escadas", "Deitar (Noturna)", "Sentar/Repouso", "Ficar em pé"]:
                        score_womac += w_op[st.selectbox(p, list(w_op.keys()), key=f"wd_{p}")]
                with c_w2:
                    st.markdown("**Rigidez (2 itens)**")
                    for p in ["Ao acordar", "Durante o dia"]:
                        score_womac += w_op[st.selectbox(p, list(w_op.keys()), key=f"wr_{p}")]
                with c_w3:
                    st.markdown("**Função - AVDs (8 itens)**")
                    for p in ["Descer escadas", "Levantar da cadeira", "Ficar em pé", "Entrar/Sair do carro", "Calçar meias", "Sair da cama", "Banho", "Tarefa doméstica"]:
                        score_womac += w_op[st.selectbox(p, list(w_op.keys()), key=f"wf_{p}")]

                max_w = (5 + 2 + 8) * 4
                pct_womac = 100 - ((score_womac / max_w) * 100)
                interp_womac = "🚨 Artrose Severa" if pct_womac < 30 else "🟡 Artrose Moderada" if pct_womac < 70 else "🟢 Artrose Leve" if pct_womac < 90 else "⭐ Excelente"
                st.info(f"📊 **Resultado WOMAC:** **{pct_womac:.1f}%** (Pontos brutos: {score_womac}) — {interp_womac}")

            # 5. KOOS
            with st.expander("🟢 Score KOOS (Lesões Gerais e O.A.)"):
                koos_op = {"Extremo / Sempre": 0, "Severo / Frequente": 1, "Moderado": 2, "Leve / Raro": 3, "Nenhum / Nunca": 4}
                c_k1, c_k2 = st.columns(2)
                score_koos = 0
                with c_k1:
                    score_koos += koos_op[st.selectbox("Sintomas e Inchaço (Média)", list(koos_op.keys()), index=4, key="k1")]
                    score_koos += koos_op[st.selectbox("Nível de Dor (Média)", list(koos_op.keys()), index=4, key="k2")]
                    score_koos += koos_op[st.selectbox("Atividades Diárias - AVDs (Média)", list(koos_op.keys()), index=4, key="k3")]
                with c_k2:
                    score_koos += koos_op[st.selectbox("Esportes e Recreação (Média)", list(koos_op.keys()), index=4, key="k4")]
                    score_koos += koos_op[st.selectbox("Qualidade de Vida (Média)", list(koos_op.keys()), index=4, key="k5")]

                pct_koos = (score_koos / 20) * 100
                interp_koos = "🚨 Risco Funcional" if pct_koos < 40 else "🟡 Limitação Moderada" if pct_koos < 80 else "🟢 Alta Performance"
                st.info(f"📊 **Resultado KOOS:** **{pct_koos:.1f}%** — {interp_koos} *(MCID: 8-10 pts | Roos 2003)*")

            # 6. IKDC
            with st.expander("✚ IKDC Subjetivo"):
                c_ik1, c_ik2 = st.columns(2)
                with c_ik1:
                    ik_dor = st.slider("Nível da Pior Dor (0=Pior, 10=Nenhuma)", 0, 10, 10, key="ik1")
                    ik_freq = st.selectbox("Frequência da Dor", ["Constante (0 pts)", "Diária (2 pts)", "Semanal (4 pts)", "Rara (7 pts)", "Nenhuma (10 pts)"], key="ik2")
                    ik_pts_freq = 0 if "0 pts" in ik_freq else 2 if "2 pts" in ik_freq else 4 if "4 pts" in ik_freq else 7 if "7 pts" in ik_freq else 10
                with c_ik2:
                    ik_func = st.slider("Função do Joelho Antes da Lesão (0-10)", 0, 10, 10, key="ik3")
                    ik_func_atual = st.slider("Função do Joelho Atual (0-10)", 0, 10, 5, key="ik4")

                score_ikdc = min(100, ((ik_dor + ik_pts_freq + (ik_func_atual * 2)) / 40) * 100)
                interp_ikdc = "🚨 Baixa Função Subjetiva" if score_ikdc < 60 else "🟡 Desempenho Moderado" if score_ikdc < 85 else "🟢 Excelente Desempenho"
                st.info(f"📊 **Resultado IKDC:** **{score_ikdc:.1f}%** — {interp_ikdc} *(MCID: 9 pts | Irrgang 2006)*")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ============================================================
    # 3. MOTOR DE SALVAMENTO INTELIGENTE (RETROCOMPATÍVEL + IA READY)
    # ============================================================
    modo_edicao = st.session_state.get("doc_id_avaliacao") is not None
    texto_botao = "🔄 ATUALIZAR AVALIAÇÃO INICIAL" if modo_edicao else "💾 SALVAR NOVA AVALIAÇÃO INICIAL"

    if st.button(texto_botao, width='stretch', type="primary"):
        def check_vazio(texto):
            return texto if texto and str(texto).strip() != "" else "Não relatado"

        if qp.strip() == "":
            toast("A 'Queixa Principal (QP)' na aba Anamnese é obrigatória para salvar o prontuário.", "error")
        else:
            # Determina Força Lesado vs Saudável para alimentar automaticamente ia_clinica.py (LSI)
            forca_ref_d = din_ext_d if (din_ext_d > 0 or din_ext_e > 0) else float(fg_ext_d)
            forca_ref_e = din_ext_e if (din_ext_d > 0 or din_ext_e > 0) else float(fg_ext_e)

            if "Direito" in lado_acometido or "Dir > Esq" in lado_acometido:
                din_lesado, din_saudavel = forca_ref_d, forca_ref_e
            elif "Esquerdo" in lado_acometido or "Esq > Dir" in lado_acometido:
                din_lesado, din_saudavel = forca_ref_e, forca_ref_d
            else:
                din_lesado, din_saudavel = min(forca_ref_d, forca_ref_e), max(forca_ref_d, forca_ref_e)

            perim_formatada = f"Dir: {perimetria_d} cm | Esq: {perimetria_e} cm"
            if perimetria_obs.strip():
                perim_formatada += f" ({perimetria_obs.strip()})"

            t_lig_comb = f"Dir: {', '.join(t_lig_d) if t_lig_d else 'Nenhum'} | Esq: {', '.join(t_lig_e) if t_lig_e else 'Nenhum'}"
            t_men_comb = f"Dir: {', '.join(t_men_d) if t_men_d else 'Nenhum'} | Esq: {', '.join(t_men_e) if t_men_e else 'Nenhum'}"
            t_pat_comb = f"Dir: {', '.join(t_pat_d) if t_pat_d else 'Nenhum'} | Esq: {', '.join(t_pat_e) if t_pat_e else 'Nenhum'}"
            zonas_comb = f"Dir: {', '.join(zonas_dor_d) if zonas_dor_d else 'Nenhuma'} | Esq: {', '.join(zonas_dor_e) if zonas_dor_e else 'Nenhuma'}"
            flex_comb = f"Dir: {', '.join(flexibilidade_d) if flexibilidade_d else 'Normal'} | Esq: {', '.join(flexibilidade_e) if flexibilidade_e else 'Normal'}"

            dados_avaliacao = {
                "Data_Avaliacao": datetime.now().strftime("%d/%m/%Y"),
                "Paciente": st.session_state.paciente,
                "Membro": st.session_state.membro_ativo,
                "Lado_Acometido": lado_acometido,
                "QP": qp,
                "HMA": check_vazio(hma),
                "Sinais_Sintomas": check_vazio(sinais_sintomas),
                "Fatores_Alivio": check_vazio(fat_alivio),
                "Fatores_Piora": check_vazio(fat_piora),
                "Tratamentos_Previos": check_vazio(trat_previos),
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
                # Campos Bilaterais Novos + Chaves Combinadas Retrocompatíveis (para Painel e PDF)
                "Derrame_Dir": derrame_d,
                "Derrame_Esq": derrame_e,
                "Derrame": f"Dir: {derrame_d} | Esq: {derrame_e}",
                "Alinhamento_Dir": alinhamento_d,
                "Alinhamento_Esq": alinhamento_e,
                "Alinhamento": f"Dir: {alinhamento_d} | Esq: {alinhamento_e}",
                "Marcha": marcha,
                "Trofismo_Dir": trofismo_d,
                "Trofismo_Esq": trofismo_e,
                "Trofismo": f"Dir: {trofismo_d} | Esq: {trofismo_e}",
                "Perimetria_Dir_cm": perimetria_d,
                "Perimetria_Esq_cm": perimetria_e,
                "Perimetria": perim_formatada,
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
                # Objetivo Funcional (PSFS + SANE)
                "Objetivo_Paciente": check_vazio(obj_paciente),
                "PSFS_Baseline": psfs_baseline,
                "SANE_Baseline_Pct": sane_baseline,
                "Distancia_Objetivo_Pct": 100 - sane_baseline,
                # Força e Dinamometria + Chaves LSI para ia_clinica.py
                "Forca_Geral_Dir": f"Ext:{fg_ext_d} Flex:{fg_flex_d} Abd:{fg_abd_d} Add:{fg_add_d}",
                "Forca_Geral_Esq": f"Ext:{fg_ext_e} Flex:{fg_flex_e} Abd:{fg_abd_e} Add:{fg_add_e}",
                "Dinamometria_Dir": f"Ext:{din_ext_d} Flex:{din_flex_d} Abd:{din_abd_d} Add:{din_add_d}",
                "Dinamometria_Esq": f"Ext:{din_ext_e} Flex:{din_flex_e} Abd:{din_abd_e} Add:{din_add_e}",
                "Dinamometria_Lesado": din_lesado,
                "Dinamometria_Saudavel": din_saudavel,
                "ADM_Joelho_Flexao": f"Dir:{adm_flex_d} Esq:{adm_flex_e}",
                "ADM_Joelho_Extensao": f"Dir:{adm_ext_d} Esq:{adm_ext_e}",
                "Lunge_Test": f"Dir:{lunge_d} Esq:{lunge_e}",
                "Flexibilidade_Dir": ", ".join(flexibilidade_d) if flexibilidade_d else "Normal",
                "Flexibilidade_Esq": ", ".join(flexibilidade_e) if flexibilidade_e else "Normal",
                "Flexibilidade": flex_comb,
                "CM_Globais": f"Marcha:{cm_marcha} | Corrida:{cm_corrida} | Salto:{cm_salto} | Agach_Bi:{cm_agach_bi}",
                "CM_Membro_Dir": f"Agach:{cm_agach_uni_d} | StepDown:{cm_step_down_d} | StepUp:{cm_step_up_d} | Afundo:{cm_afundo_d} | Eq:{cm_eq_uni_d}",
                "CM_Membro_Esq": f"Agach:{cm_agach_uni_e} | StepDown:{cm_step_down_e} | StepUp:{cm_step_up_e} | Afundo:{cm_afundo_e} | Eq:{cm_eq_uni_e}",
                "Exames_Apresentados": ", ".join(tipos_exames) if tipos_exames else "Nenhum",
                "Testes_Alvo": testes_alvo,
                "LEFS_Pct": pct_lefs,
                "LEFS_Pts_80": pts_lefs_80,
                "Interpretacao_LEFS": interp_lefs,
                "VISA_P_Pts": score_visap,
                "Interpretacao_VISA_P": interp_visap,
                "Lysholm_Pts": score_lysholm,
                "Interpretacao_Lysholm": interp_lysholm,
                "WOMAC_Pct": pct_womac,
                "Interpretacao_WOMAC": interp_womac,
                "KOOS_Pct": pct_koos,
                "IKDC_Pct": score_ikdc,
                "Profissional_ID": st.session_state.get("user_email", "admin"),
            }

            with st.spinner("Sincronizando Avaliação Inicial com o Firebase..."):
                try:
                    if modo_edicao:
                        db.collection("Avaliacao_Inicial").document(st.session_state.doc_id_avaliacao).update(dados_avaliacao)
                        invalidar_cache("Avaliacao_Inicial")
                        toast("Avaliação Inicial atualizada com sucesso!", "success")
                    else:
                        db.collection("Avaliacao_Inicial").add(dados_avaliacao)
                        invalidar_cache("Avaliacao_Inicial")
                        toast("Nova Avaliação Inicial salva com sucesso!", "success")
                except Exception as e:
                    toast(f"Erro ao comunicar com a base de dados: {e}", "error")
