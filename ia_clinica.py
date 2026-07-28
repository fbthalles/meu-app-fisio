"""
GENUA | Módulo de IA Clínica Baseada em Evidência
==================================================

Este módulo é o CÉREBRO CLÍNICO do app. Todas as regras aqui são fundamentadas
em literatura peer-reviewed, com referências científicas explícitas.

Princípios inegociáveis:
- Regras clínicas EXPLÍCITAS, não LLM gerando parecer.
- Cada threshold vem de estudo peer-reviewed citado.
- Toda decisão é AUDITÁVEL: fisio pode conferir a regra.
- Retorno em dict estruturado, nunca texto livre.

Estrutura:
    - CONSTANTES CLÍNICAS: MCID, thresholds LSI, definições de bandeiras.
    - analisar_estagnacao(historico, score)     → detecta estagnação por MCID
    - calcular_lsi(lado_lesado, lado_saudavel)  → LSI + classificação de risco
    - analisar_bandeiras(avaliacao)             → red/yellow/blue flags
    - analisar_paciente(paciente_nome)          → orquestra tudo (função pública)
    - renderizar_insights(insights, cores)      → renderiza no Streamlit
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from firebase_client import conn


# ============================================================
# CONSTANTES CLÍNICAS (com referência científica)
# ============================================================

# --- MCID (Minimal Clinically Important Difference) ---
MCID = {
    "Dor": {
        "valor": 2.0,
        "unidade": "pontos na EVA",
        "referencia": "Salaffi 2004 (doi:10.1016/j.ejpain.2003.09.004)"
    },
    "LEFS": {
        "valor": 9.0,
        "unidade": "pontos",
        "referencia": "Binkley 1999"
    },
    "KOOS": {
        "valor": 8.0,   # limite inferior conservador (8-10 pts por subescala)
        "unidade": "pontos por subescala",
        "referencia": "Roos 2003"
    },
    "VISA_P": {
        "valor": 13.0,
        "unidade": "pontos",
        "referencia": "Hernandez-Sanchez 2014"
    },
    "Lysholm": {
        "valor": 10.0,
        "unidade": "pontos",
        "referencia": "Briggs 2009"
    },
    "IKDC": {
        "valor": 9.0,
        "unidade": "pontos",
        "referencia": "Irrgang 2006"
    }
}

# --- Detector de estagnação ---
SESSOES_MINIMAS_ESTAGNACAO = 5    # bem conservador (Edgar Jun/2026)

# --- LSI (Limb Symmetry Index) thresholds pós-LCA ---
LSI_ALTA_FUNCIONAL = 90.0     # ≥90% = critério de alta funcional
LSI_ATENCAO = 85.0            # 85-89% = zona de atenção
LSI_REF = "Grindem 2016 (doi:10.1136/bjsports-2016-096031)"


# ============================================================
# NORMALIZAÇÃO DE DIAGNÓSTICO (preparação p/ gráficos contextuais)
# ============================================================
# Detecta o fenótipo clínico a partir do texto livre digitado pelo fisio.
# Cada fenótipo define quais métricas devem ser plotadas no painel:
#   - Tendinopatia: dor + carga excêntrica (não ADM!)
#   - Pós-LCA: dor + flexão + extensão + LSI
#   - Condromalácia: dor + dor em funcionais (agachamento, escada)
#   - Meniscopatia: dor + ADM + bloqueio articular
#   - Artrose: dor + rigidez matinal + WOMAC
FENOTIPOS = {
    "pos_lca": {
        "label": "Pós-LCA (Reconstrução do Ligamento Cruzado Anterior)",
        "keywords": ["lca", "cruzado anterior", "cruzado ant", "reconstrucao lca", "reconstrução lca", "acl"],
        "metricas_relevantes": ["Dor", "Flexao", "Extensao", "LSI"],
        "prom_principal": "IKDC",
        "tempo_esperado_semanas": 36,
    },
    "tendinopatia_patelar": {
        "label": "Tendinopatia Patelar (Jumper's Knee)",
        "keywords": ["tendinopatia patelar", "jumper", "tendinite patelar", "tendinose patelar", "visa-p", "visa_p"],
        "metricas_relevantes": ["Dor", "Carga_Excentrica"],
        "prom_principal": "VISA_P",
        "tempo_esperado_semanas": 24,
    },
    "tendinopatia_quadriceps": {
        "label": "Tendinopatia do Quadríceps",
        "keywords": ["tendinopatia quadriceps", "tendinopatia quadrícipe", "tendinite quadriceps"],
        "metricas_relevantes": ["Dor", "Carga_Excentrica"],
        "prom_principal": "VISA_P",
        "tempo_esperado_semanas": 24,
    },
    "condromalacia": {
        "label": "Condromalácia / Síndrome Patelofemoral",
        "keywords": ["condromalacia", "condromalácia", "patelofemoral", "condropatia", "sfp"],
        "metricas_relevantes": ["Dor", "Testes_Funcionais"],
        "prom_principal": "KOOS",
        "tempo_esperado_semanas": 12,
    },
    "meniscopatia": {
        "label": "Lesão Meniscal",
        "keywords": ["menisco", "meniscopatia", "meniscectomia", "sutura meniscal"],
        "metricas_relevantes": ["Dor", "Flexao", "Extensao"],
        "prom_principal": "Lysholm",
        "tempo_esperado_semanas": 16,
    },
    "artrose_joelho": {
        "label": "Osteoartrose do Joelho",
        "keywords": ["artrose", "osteoartrose", "osteoartrite", "oa", "gonartrose"],
        "metricas_relevantes": ["Dor", "Rigidez", "Funcao"],
        "prom_principal": "WOMAC",
        "tempo_esperado_semanas": 24,
    },
    "lcm_lcl": {
        "label": "Lesão de Ligamento Colateral (LCM/LCL)",
        "keywords": ["colateral", "lcm", "lcl", "ligamento colateral"],
        "metricas_relevantes": ["Dor", "Flexao", "Extensao"],
        "prom_principal": "IKDC",
        "tempo_esperado_semanas": 12,
    },
}


def normalizar_diagnostico(texto_diagnostico: str) -> dict:
    """
    Detecta o fenótipo clínico a partir do texto livre de diagnóstico.

    Args:
        texto_diagnostico: texto digitado pelo fisio no cadastro
                           (ex: "Pós-op LCA", "condromalácia", "VISA-P baixo")

    Returns:
        dict com {fenotipo, label, metricas_relevantes, prom_principal, tempo_esperado_semanas}
        Se não reconhecer, retorna fenotipo "generico" com métricas padrão.
    """
    if not texto_diagnostico:
        return {
            "fenotipo": "generico",
            "label": "Não especificado",
            "metricas_relevantes": ["Dor", "Flexao"],
            "prom_principal": "Lysholm",
            "tempo_esperado_semanas": None,
        }

    texto = str(texto_diagnostico).lower().strip()

    for fenotipo, cfg in FENOTIPOS.items():
        for keyword in cfg["keywords"]:
            if keyword in texto:
                return {
                    "fenotipo": fenotipo,
                    "label": cfg["label"],
                    "metricas_relevantes": cfg["metricas_relevantes"],
                    "prom_principal": cfg["prom_principal"],
                    "tempo_esperado_semanas": cfg["tempo_esperado_semanas"],
                }

    return {
        "fenotipo": "generico",
        "label": f"Não reconhecido ({texto_diagnostico})",
        "metricas_relevantes": ["Dor", "Flexao"],
        "prom_principal": "Lysholm",
        "tempo_esperado_semanas": None,
    }


# --- Bandeiras clínicas ---
BANDEIRAS = {
    "vermelha": {
        "cor": "🔴",
        "descricao": "Sinal de patologia grave (fratura, tumor, infecção)",
        "acao": "Encaminhar/reencaminhar avaliação médica",
        "referencia": "Greenhalgh 2006 (Red flags in musculoskeletal medicine)"
    },
    "amarela": {
        "cor": "🟡",
        "descricao": "Fator psicossocial (medo, catastrofização)",
        "acao": "Considerar aplicação da Tampa Scale (TSK-11)",
        "referencia": "Nicholas 2011 (early identification of psychosocial risk)"
    },
    "azul": {
        "cor": "🔵",
        "descricao": "Barreiras do ambiente de trabalho",
        "acao": "Abordar contexto ocupacional no plano",
        "referencia": "Main 2010 (Blue and Black flags)"
    },
    "negra": {
        "cor": "⚫",
        "descricao": "Barreiras sistêmicas (seguros, processos)",
        "acao": "Considerar impacto sistêmico na recuperação",
        "referencia": "Main 2010"
    }
}


# ============================================================
# FUNÇÃO 1: Detector de Estagnação por MCID
# ============================================================
def analisar_estagnacao(historico: list, score: str = "Dor") -> dict:
    """
    Detecta estagnação clínica: se as últimas N sessões não apresentaram
    delta ≥ MCID, considera-se que o paciente parou de evoluir.

    Args:
        historico: lista cronológica dos valores do score (ex: [7, 6, 5, 5, 5])
        score: nome do score ("Dor", "LEFS", "KOOS", "VISA_P", "Lysholm", "IKDC")

    Returns:
        dict com {status, delta, mcid, sessoes_analisadas, racional, referencia}
    """
    if score not in MCID:
        return {"status": "indefinido", "racional": f"Score {score} não catalogado"}

    mcid_valor = MCID[score]["valor"]
    ref = MCID[score]["referencia"]

    if len(historico) < SESSOES_MINIMAS_ESTAGNACAO:
        return {
            "status": "insuficiente",
            "score": score,
            "sessoes_analisadas": len(historico),
            "sessoes_necessarias": SESSOES_MINIMAS_ESTAGNACAO,
            "racional": f"Necessárias ≥{SESSOES_MINIMAS_ESTAGNACAO} sessões para avaliar estagnação. Há {len(historico)}.",
            "referencia": ref
        }

    janela = historico[-SESSOES_MINIMAS_ESTAGNACAO:]

    # Para dor: melhora = redução; para funcionais: melhora = aumento
    if score == "Dor":
        delta = max(janela) - min(janela)      # amplitude simples
        melhora = janela[0] - janela[-1]       # positivo = dor caindo
    else:
        delta = max(janela) - min(janela)
        melhora = janela[-1] - janela[0]       # positivo = função subindo

    if abs(melhora) < mcid_valor:
        status = "estagnacao"
        racional = (
            f"Últimas {SESSOES_MINIMAS_ESTAGNACAO} sessões: variação de {melhora:+.1f} "
            f"< MCID ({mcid_valor} {MCID[score]['unidade']}). "
            f"Sem melhora clinicamente significativa. Considere revisar o plano."
        )
    elif melhora >= mcid_valor:
        status = "melhora"
        racional = (
            f"Últimas {SESSOES_MINIMAS_ESTAGNACAO} sessões: melhora de {melhora:+.1f} "
            f"≥ MCID ({mcid_valor}). Evolução clinicamente significativa."
        )
    else:
        status = "piora"
        racional = (
            f"Últimas {SESSOES_MINIMAS_ESTAGNACAO} sessões: piora de {melhora:+.1f}. "
            f"Investigar causa (adesão, sobrecarga, novo trauma)."
        )

    return {
        "status": status,
        "score": score,
        "delta": round(melhora, 2),
        "mcid": mcid_valor,
        "sessoes_analisadas": SESSOES_MINIMAS_ESTAGNACAO,
        "racional": racional,
        "referencia": ref
    }


# ============================================================
# FUNÇÃO 2: Cálculo de LSI (Limb Symmetry Index)
# ============================================================
def calcular_lsi(lado_lesado: float, lado_saudavel: float) -> dict:
    """
    Calcula o Limb Symmetry Index e classifica o risco de re-lesão.

    LSI = (lado_lesado / lado_saudavel) * 100

    Thresholds da literatura (Grindem 2016):
        ≥90% = apto para alta funcional
        85-89% = zona de atenção
        <85% = risco 2-4x aumentado de re-lesão

    Args:
        lado_lesado: valor do teste no lado lesado (força, distância, etc.)
        lado_saudavel: valor do teste no lado contralateral saudável

    Returns:
        dict com {valor, classificacao, cor, acao, referencia}
    """
    if not lado_saudavel or lado_saudavel <= 0:
        return {
            "valor": None,
            "classificacao": "indefinido",
            "racional": "Dados do lado saudável insuficientes para calcular LSI.",
            "referencia": LSI_REF
        }

    lsi = (lado_lesado / lado_saudavel) * 100

    if lsi >= LSI_ALTA_FUNCIONAL:
        classificacao = "alta_funcional"
        cor = "🟢"
        acao = "Simetria adequada. Critério de alta funcional atingido."
    elif lsi >= LSI_ATENCAO:
        classificacao = "atencao"
        cor = "🟡"
        acao = "Zona de atenção. Progredir carga com cautela antes da alta."
    else:
        classificacao = "risco"
        cor = "🔴"
        acao = f"LSI < {LSI_ATENCAO}%. Risco de re-lesão 2-4x aumentado. NÃO liberar para alta."

    return {
        "valor": round(lsi, 1),
        "classificacao": classificacao,
        "cor": cor,
        "acao": acao,
        "referencia": LSI_REF
    }


# ============================================================
# FUNÇÃO 3: Análise de Bandeiras
# ============================================================
def analisar_bandeiras(avaliacao: dict) -> list:
    """
    Analisa a avaliação inicial e detecta bandeiras clínicas ativas.

    Args:
        avaliacao: dict com dados da Avaliacao_Inicial (do Firestore)

    Returns:
        lista de dicts, cada um representando uma bandeira ativa.
    """
    bandeiras_ativas = []

    # --- Bandeiras Vermelhas ---
    red_flags = avaliacao.get("Red_Flags", []) or avaliacao.get("Bandeiras_Vermelhas", [])
    if isinstance(red_flags, str):
        red_flags = [red_flags]

    for flag in (red_flags or []):
        if flag and str(flag).strip().lower() not in ["não", "nao", "nenhum", "", "n/a"]:
            bandeiras_ativas.append({
                "tipo": "vermelha",
                "cor": BANDEIRAS["vermelha"]["cor"],
                "gatilho": flag,
                "descricao": BANDEIRAS["vermelha"]["descricao"],
                "acao": BANDEIRAS["vermelha"]["acao"],
                "referencia": BANDEIRAS["vermelha"]["referencia"]
            })

    # --- Bandeiras Amarelas (psicossociais) ---
    yellow_flags = avaliacao.get("Yellow_Flags", []) or avaliacao.get("Bandeiras_Amarelas", [])
    if isinstance(yellow_flags, str):
        yellow_flags = [yellow_flags]

    for flag in (yellow_flags or []):
        if flag and str(flag).strip().lower() not in ["não", "nao", "nenhum", "", "n/a"]:
            bandeiras_ativas.append({
                "tipo": "amarela",
                "cor": BANDEIRAS["amarela"]["cor"],
                "gatilho": flag,
                "descricao": BANDEIRAS["amarela"]["descricao"],
                "acao": BANDEIRAS["amarela"]["acao"],
                "referencia": BANDEIRAS["amarela"]["referencia"]
            })

    # --- Bandeiras Azuis (trabalho) ---
    blue_flags = avaliacao.get("Blue_Flags", []) or avaliacao.get("Bandeiras_Azuis", [])
    if isinstance(blue_flags, str):
        blue_flags = [blue_flags]

    for flag in (blue_flags or []):
        if flag and str(flag).strip().lower() not in ["não", "nao", "nenhum", "", "n/a"]:
            bandeiras_ativas.append({
                "tipo": "azul",
                "cor": BANDEIRAS["azul"]["cor"],
                "gatilho": flag,
                "descricao": BANDEIRAS["azul"]["descricao"],
                "acao": BANDEIRAS["azul"]["acao"],
                "referencia": BANDEIRAS["azul"]["referencia"]
            })

    # --- Dor noturna (regra clínica automática) ---
    dor_noturna = str(avaliacao.get("Dor_Noturna", "")).strip().lower()
    if dor_noturna in ["sim", "s", "presente", "true", "yes"]:
        bandeiras_ativas.append({
            "tipo": "vermelha",
            "cor": BANDEIRAS["vermelha"]["cor"],
            "gatilho": "Dor noturna persistente relatada",
            "descricao": "Padrão inflamatório ou não-mecânico",
            "acao": "Considerar reavaliação médica",
            "referencia": "Greenhalgh 2006"
        })

    return bandeiras_ativas


# ============================================================
# FUNÇÃO 4 (ORQUESTRADORA): analisar_paciente
# ============================================================
def analisar_paciente(paciente_nome: str) -> dict:
    """
    Função pública principal: recebe o nome do paciente, busca todos os dados
    no Firestore e retorna um dashboard clínico completo.

    Args:
        paciente_nome: nome do paciente (string, chave usada nas coleções)

    Returns:
        dict com estrutura:
        {
            "paciente": str,
            "gerado_em": str (ISO),
            "estagnacao": {...},        # análise de estagnação por Dor
            "estagnacao_funcional": {...},  # se houver LEFS/KOOS
            "lsi": {...},               # LSI atual se calculável
            "bandeiras": [...],         # lista de bandeiras ativas
            "sessoes_registradas": int
        }
    """
    resultado = {
        "paciente": paciente_nome,
        "gerado_em": datetime.now().isoformat(),
        "fenotipo": None,
        "estagnacao": None,
        "estagnacao_funcional": None,
        "lsi": None,
        "bandeiras": [],
        "sessoes_registradas": 0
    }

    # --- 0. FENÓTIPO CLÍNICO (leitura do Cadastro) ---
    try:
        df_cad = conn.read("Cadastro")
        registro = df_cad[df_cad["Nome"].astype(str).str.strip() == paciente_nome]
        if not registro.empty:
            dx_texto = registro.iloc[-1].get("Diagnostico_Clinico", "")
            resultado["fenotipo"] = normalizar_diagnostico(dx_texto)
    except Exception:
        resultado["fenotipo"] = normalizar_diagnostico("")

    # --- 1. LEITURA DO HISTÓRICO (Evolucao) ---
    try:
        df_evo = conn.read_paciente("Evolucao", paciente_nome)
    except Exception:
        df_evo = pd.DataFrame()

    if not df_evo.empty:
        # Ordena por data
        if "Data" in df_evo.columns:
            df_evo["_Data_dt"] = pd.to_datetime(df_evo["Data"], errors="coerce")
            df_evo = df_evo.sort_values("_Data_dt")

        resultado["sessoes_registradas"] = len(df_evo)

        # --- Análise de estagnação da Dor (EVA) ---
        if "Dor" in df_evo.columns:
            historico_dor = pd.to_numeric(df_evo["Dor"], errors="coerce").dropna().tolist()
            if historico_dor:
                resultado["estagnacao"] = analisar_estagnacao(historico_dor, "Dor")

    # --- 2. LEITURA DA AVALIAÇÃO (Avaliacao_Inicial) ---
    try:
        df_aval = conn.read_paciente("Avaliacao_Inicial", paciente_nome)
    except Exception:
        df_aval = pd.DataFrame()

    if not df_aval.empty:
        # Pega a avaliação mais recente
        if "Data_Avaliacao" in df_aval.columns:
            df_aval["_Data_dt"] = pd.to_datetime(df_aval["Data_Avaliacao"], errors="coerce")
            df_aval = df_aval.sort_values("_Data_dt")
        ultima_aval = df_aval.iloc[-1].to_dict()

        # --- Bandeiras ---
        resultado["bandeiras"] = analisar_bandeiras(ultima_aval)

        # --- LSI (se houver dinamometria bilateral) ---
        lado_lesado = ultima_aval.get("Forca_Lesado") or ultima_aval.get("Dinamometria_Lesado")
        lado_saudavel = ultima_aval.get("Forca_Saudavel") or ultima_aval.get("Dinamometria_Saudavel")
        try:
            if lado_lesado is not None and lado_saudavel is not None:
                resultado["lsi"] = calcular_lsi(float(lado_lesado), float(lado_saudavel))
        except (ValueError, TypeError):
            pass

        # --- Estagnação Funcional (LEFS, KOOS se coletados no check-in) ---
        for score_func in ["LEFS", "KOOS"]:
            if score_func in df_evo.columns:
                hist = pd.to_numeric(df_evo[score_func], errors="coerce").dropna().tolist()
                if hist:
                    resultado["estagnacao_funcional"] = analisar_estagnacao(hist, score_func)
                    break     # usa o primeiro disponível

    return resultado


# ============================================================
# RENDERIZAÇÃO NO STREAMLIT (chamada pelo modulo_painel)
# ============================================================
def renderizar_insights(insights: dict, cores: dict):
    """
    Renderiza o dashboard de IA Clínica dentro de uma aba do painel.

    Args:
        insights: resultado de analisar_paciente()
        cores: dict CORES_GENUA (para manter identidade visual)
    """
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, {cores['primaria']} 0%, {cores['secundaria']} 100%);
                    padding: 20px; border-radius: 16px; color: white; margin-bottom: 20px;'>
            <h3 style='color: white; margin: 0;'>🧠 Insights Clínicos — IA Baseada em Evidência</h3>
            <p style='color: #E0F7FA; margin: 8px 0 0 0; font-size: 0.95rem;'>
                Análise automatizada de estagnação, simetria e bandeiras clínicas.
                Todas as regras têm referência científica documentada.
            </p>
        </div>
    """, unsafe_allow_html=True)

    if insights["sessoes_registradas"] == 0:
        st.info("ℹ️ Paciente ainda sem sessões de check-in registradas. Os insights aparecerão após os primeiros atendimentos.")
        return

    # ==== FENÓTIPO CLÍNICO ====
    fen = insights.get("fenotipo") or {}
    if fen.get("fenotipo") and fen["fenotipo"] != "generico":
        st.markdown(
            f"<div style='background: {cores['fundo_claro']}; border-left: 4px solid {cores['secundaria']}; "
            f"padding: 12px 16px; border-radius: 8px; margin-bottom: 15px;'>"
            f"<strong style='color: {cores['primaria']};'>🎯 Fenótipo Clínico Identificado:</strong> {fen['label']}<br>"
            f"<small style='color: {cores['texto_suave']};'>Foco de análise: {', '.join(fen['metricas_relevantes'])} "
            f"| PROM principal: {fen['prom_principal']} "
            f"| Tempo esperado de reabilitação: {fen['tempo_esperado_semanas']} semanas</small>"
            f"</div>",
            unsafe_allow_html=True,
        )
    elif fen.get("fenotipo") == "generico":
        st.caption(f"ℹ️ Fenótipo não reconhecido pelo algoritmo. Considere padronizar o Diagnóstico Clínico no Cadastro para análise contextual.")

    # ==== KPIs no topo ====
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📅 Sessões Registradas", insights["sessoes_registradas"])
    with col2:
        n_bandeiras = len(insights["bandeiras"])
        st.metric("🚩 Bandeiras Ativas", n_bandeiras, delta=None if n_bandeiras == 0 else "Atenção")
    with col3:
        if insights["lsi"] and insights["lsi"].get("valor"):
            st.metric(f"{insights['lsi']['cor']} LSI", f"{insights['lsi']['valor']}%")
        else:
            st.metric("📊 LSI", "N/D", help="Sem dinamometria bilateral registrada")

    st.markdown("---")

    # ==== ESTAGNAÇÃO — DOR ====
    st.markdown(f"<h4 style='color: {cores['primaria']};'>📉 Análise de Estagnação — Dor (EVA)</h4>", unsafe_allow_html=True)
    est = insights["estagnacao"]

    if est is None or est.get("status") == "insuficiente":
        n_atual = est["sessoes_analisadas"] if est else 0
        st.info(f"⏳ Aguardando dados: análise requer ≥ {SESSOES_MINIMAS_ESTAGNACAO} sessões (há {n_atual}).")
    elif est["status"] == "estagnacao":
        st.warning(f"🟡 **ESTAGNAÇÃO DETECTADA**\n\n{est['racional']}")
        st.caption(f"📚 Referência: {est['referencia']}")
    elif est["status"] == "melhora":
        st.success(f"🟢 **EVOLUÇÃO POSITIVA**\n\n{est['racional']}")
        st.caption(f"📚 Referência: {est['referencia']}")
    elif est["status"] == "piora":
        st.error(f"🔴 **PIORA CLÍNICA**\n\n{est['racional']}")
        st.caption(f"📚 Referência: {est['referencia']}")

    # ==== LSI ====
    if insights["lsi"] and insights["lsi"].get("valor") is not None:
        st.markdown(f"<h4 style='color: {cores['primaria']};'>⚖️ Limb Symmetry Index (LSI)</h4>", unsafe_allow_html=True)
        lsi_data = insights["lsi"]

        if lsi_data["classificacao"] == "alta_funcional":
            st.success(f"{lsi_data['cor']} **LSI {lsi_data['valor']}%** — {lsi_data['acao']}")
        elif lsi_data["classificacao"] == "atencao":
            st.warning(f"{lsi_data['cor']} **LSI {lsi_data['valor']}%** — {lsi_data['acao']}")
        else:
            st.error(f"{lsi_data['cor']} **LSI {lsi_data['valor']}%** — {lsi_data['acao']}")

        st.caption(f"📚 Referência: {lsi_data['referencia']}")

    # ==== BANDEIRAS ====
    st.markdown(f"<h4 style='color: {cores['primaria']};'>🚩 Bandeiras Clínicas Ativas</h4>", unsafe_allow_html=True)

    if not insights["bandeiras"]:
        st.success("✅ Nenhuma bandeira clínica ativa. Perfil de baixo risco.")
    else:
        for b in insights["bandeiras"]:
            if b["tipo"] == "vermelha":
                st.error(f"{b['cor']} **BANDEIRA VERMELHA** — {b['gatilho']}\n\n_{b['descricao']}_\n\n**Ação:** {b['acao']}")
            elif b["tipo"] == "amarela":
                st.warning(f"{b['cor']} **BANDEIRA AMARELA** — {b['gatilho']}\n\n_{b['descricao']}_\n\n**Ação:** {b['acao']}")
            else:
                st.info(f"{b['cor']} **BANDEIRA {b['tipo'].upper()}** — {b['gatilho']}\n\n_{b['descricao']}_\n\n**Ação:** {b['acao']}")
            st.caption(f"📚 Referência: {b['referencia']}")
