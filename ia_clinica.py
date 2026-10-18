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
    - CONSTANTES CLÍNICAS: MCID, thresholds LSI, GROC, PASS, PSFS/SANE e bandeiras.
    - analisar_estagnacao(historico, score)           → detecta estagnação por MCID
    - calcular_lsi(lado_lesado, lado_saudavel, fonte) → LSI + classificação de risco (Exclusivo Dinamometria)
    - analisar_percepcao_metas(avaliacao, df_evo)     → GROC, PASS, SANE e PSFS
    - analisar_bandeiras(avaliacao)                   → red/yellow/blue/black flags
    - analisar_paciente(paciente_nome)                → orquestra tudo (função pública)
    - renderizar_insights(insights, cores)            → renderiza no Streamlit
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config import titulo, secao
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
        "referencia": "Binkley 1999 (Physical Therapy)"
    },
    "KOOS": {
        "valor": 8.0,   # limite inferior conservador (8-10 pts por subescala)
        "unidade": "pontos por subescala",
        "referencia": "Roos 2003 (Health Qual Life Outcomes)"
    },
    "VISA_P": {
        "valor": 13.0,
        "unidade": "pontos",
        "referencia": "Hernandez-Sanchez 2014 (BJSM)"
    },
    "Lysholm": {
        "valor": 10.0,
        "unidade": "pontos",
        "referencia": "Briggs 2009 (AJSM)"
    },
    "IKDC": {
        "valor": 9.0,
        "unidade": "pontos",
        "referencia": "Irrgang 2006 (AJSM)"
    },
    "PSFS": {
        "valor": 2.0,
        "unidade": "pontos (0-10)",
        "referencia": "Stratford 1995 / Hefford 2012 (JOSPT)"
    },
    "GROC": {
        "valor": 3.0,
        "unidade": "pontos (-5 a +5)",
        "referencia": "Kamper 2009 (JOSPT)"
    },
    "SANE": {
        "valor": 15.0,
        "unidade": "% de capacidade",
        "referencia": "Shelbourne 2009 / Winterstein 2013"
    }
}

# --- Detector de estagnação ---
SESSOES_MINIMAS_ESTAGNACAO = 5

# --- LSI (Limb Symmetry Index) thresholds pós-LCA ---
LSI_ALTA_FUNCIONAL = 90.0     # ≥90% = critério de alta funcional
LSI_ATENCAO = 85.0            # 85-89% = zona de atenção
LSI_REF = "Grindem 2016 (doi:10.1136/bjsports-2016-096031)"


# ============================================================
# NORMALIZAÇÃO DE DIAGNÓSTICO (preparação p/ gráficos contextuais)
# ============================================================
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
        "keywords": ["condromalacia", "condromalácia", "patelofemoral", "condropatia", "sfp", "femoropatelar"],
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
    """Detecta o fenótipo clínico a partir do texto livre de diagnóstico."""
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
        "descricao": "Sinal de patologia grave (fratura, tumor, infecção, TVP)",
        "acao": "Encaminhar/reencaminhar imediatamente para avaliação médica",
        "referencia": "Greenhalgh 2006 (Red flags in musculoskeletal medicine)"
    },
    "amarela": {
        "cor": "🟡",
        "descricao": "Fator psicossocial / cognitivo-emocional (medo, catastrofização)",
        "acao": "Aplicar educação em dor, exposição graduada e considerar Tampa Scale (TSK-11)",
        "referencia": "Nicholas 2011 (Early identification of psychosocial risk)"
    },
    "azul": {
        "cor": "🔵",
        "descricao": "Barreiras ocupacionais / demandas biomecânicas do trabalho",
        "acao": "Adaptar volume de carga à rotina laboral e planejar retorno gradual",
        "referencia": "Main 2010 (Blue and Black flags in occupational rehabilitation)"
    },
    "negra": {
        "cor": "⚫",
        "descricao": "Barreiras sistêmicas, previdenciárias ou médico-legais (INSS, litígio)",
        "acao": "Documentar evolução objetiva rigorosa (LSI, ADM, PROMs) e alinhar expectativas",
        "referencia": "Main 2010 (Contextual and systemic obstacles to recovery)"
    }
}


# ============================================================
# HELPERS INTERNOS DE EXTRAÇÃO SEGURA (RETROCOMPATIBILIDADE)
# ============================================================
def _extrair_valor_prefixo(texto_bruto, prefixo: str = "Ext") -> float:
    """
    Extrai um float de strings formatadas como 'Ext:35.0 Flex:20.0 Abd:15.0 Add:15.0'.
    Retorna 0.0 se não encontrar.
    """
    if texto_bruto is None or pd.isna(texto_bruto):
        return 0.0
    if isinstance(texto_bruto, (int, float)):
        return float(texto_bruto)
    try:
        partes = str(texto_bruto).replace("|", " ").split()
        for p in partes:
            if p.startswith(prefixo + ":"):
                return float(p.split(":")[1].replace(",", "."))
    except (ValueError, TypeError, IndexError):
        pass
    return 0.0


def _normalizar_lista_flags(valor_bruto) -> list:
    """Converte string separada por vírgulas ou lista em lista limpa de strings."""
    if valor_bruto is None or (isinstance(valor_bruto, float) and pd.isna(valor_bruto)):
        return []
    if isinstance(valor_bruto, list):
        itens = [str(x).strip() for x in valor_bruto if x is not None]
    else:
        itens = [x.strip() for x in str(valor_bruto).split(",")]
    termos_vazios = {"não", "nao", "nenhum", "nenhuma", "", "n/a", "normal", "sem dor", "none"}
    return [i for i in itens if i and i.lower() not in termos_vazios]


# ============================================================
# FUNÇÃO 1: Detector de Estagnação por MCID
# ============================================================
def analisar_estagnacao(historico: list, score: str = "Dor") -> dict:
    """
    Detecta estagnação clínica: se as últimas N sessões não apresentaram
    delta ≥ MCID, considera-se que o paciente parou de evoluir.
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

    if score == "Dor":
        melhora = janela[0] - janela[-1]
    else:
        melhora = janela[-1] - janela[0]

    if abs(melhora) < mcid_valor:
        status = "estagnacao"
        racional = (
            f"Últimas {SESSOES_MINIMAS_ESTAGNACAO} sessões: variação de {melhora:+.1f} "
            f"< MCID ({mcid_valor} {MCID[score]['unidade']}). "
            f"Sem melhora clinicamente significativa. Considere revisar o plano e progressão de carga."
        )
    elif melhora >= mcid_valor:
        status = "melhora"
        racional = (
            f"Últimas {SESSOES_MINIMAS_ESTAGNACAO} sessões: melhora de {melhora:+.1f} "
            f"≥ MCID ({mcid_valor} {MCID[score]['unidade']}). Evolução clinicamente significativa."
        )
    else:
        status = "piora"
        racional = (
            f"Últimas {SESSOES_MINIMAS_ESTAGNACAO} sessões: piora de {melhora:+.1f} "
            f"({MCID[score]['unidade']}). Investigar causa (adesão, sobrecarga mecânica ou novo trauma)."
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
# FUNÇÃO 2: Cálculo de LSI (Limb Symmetry Index — Exclusivo Dinamometria)
# ============================================================
def calcular_lsi(lado_lesado: float, lado_saudavel: float, fonte: str = "Dinamometria Quadríceps (kgf)") -> dict:
    """
    Calcula o Limb Symmetry Index e classifica o risco de re-lesão.
    LSI = (lado_lesado / lado_saudavel) * 100
    """
    if lado_saudavel is None or lado_saudavel <= 0 or lado_lesado is None or lado_lesado < 0:
        return {
            "valor": None,
            "classificacao": "indefinido",
            "fonte": fonte,
            "racional": "Dinamometria bilateral (kgf) não preenchida para calcular LSI.",
            "referencia": LSI_REF
        }

    lsi = (lado_lesado / lado_saudavel) * 100.0

    if lsi >= LSI_ALTA_FUNCIONAL:
        classificacao = "alta_funcional"
        cor = "🟢"
        acao = f"Simetria adequada ({fonte}: {lado_lesado:.1f} vs {lado_saudavel:.1f} kgf). Critério de alta funcional atingido."
    elif lsi >= LSI_ATENCAO:
        classificacao = "atencao"
        cor = "🟡"
        acao = f"Zona de atenção ({fonte}: {lado_lesado:.1f} vs {lado_saudavel:.1f} kgf). Progredir carga unilateral com cautela antes da alta."
    else:
        classificacao = "risco"
        cor = "🔴"
        acao = f"LSI < {LSI_ATENCAO}% ({fonte}: {lado_lesado:.1f} vs {lado_saudavel:.1f} kgf). Risco de re-lesão 2-4x aumentado. NÃO liberar para alta."

    return {
        "valor": round(lsi, 1),
        "lado_lesado": round(lado_lesado, 1),
        "lado_saudavel": round(lado_saudavel, 1),
        "fonte": fonte,
        "classificacao": classificacao,
        "cor": cor,
        "acao": acao,
        "referencia": LSI_REF
    }


# ============================================================
# FUNÇÃO 3: Análise de Percepção do Paciente & Metas (GROC, PASS, SANE, PSFS)
# ============================================================
def analisar_percepcao_metas(avaliacao: dict, df_evo: pd.DataFrame) -> dict:
    """
    Analisa o alinhamento entre a meta funcional inicial do paciente (PSFS/SANE)
    e a percepção longitudinal nas sessões de check-in (GROC, PASS e evolução do SANE).
    """
    objetivo = str(avaliacao.get("Objetivo_Paciente", "Não especificado") or "Não especificado")
    if objetivo == "Não relatado":
        objetivo = "Não especificado"

    try:
        psfs_base = int(float(avaliacao.get("PSFS_Baseline", 3) or 3))
    except (ValueError, TypeError):
        psfs_base = 3

    try:
        sane_base = float(avaliacao.get("SANE_Baseline_Pct", 30.0) or 30.0)
    except (ValueError, TypeError):
        sane_base = 30.0

    sane_atual = sane_base
    groc_score = None
    groc_label = "Não registrado"
    pass_atingido = None
    pass_label = "Não registrado"

    if not df_evo.empty:
        ultima_sessao = df_evo.iloc[-1]
        if "SANE_Pct" in df_evo.columns and pd.notna(ultima_sessao.get("SANE_Pct")):
            try:
                sane_atual = float(ultima_sessao.get("SANE_Pct"))
            except (ValueError, TypeError):
                sane_atual = sane_base

        if "GROC_Score" in df_evo.columns and pd.notna(ultima_sessao.get("GROC_Score")):
            try:
                groc_score = int(float(ultima_sessao.get("GROC_Score")))
            except (ValueError, TypeError):
                groc_score = None

        if "GROC_Label" in df_evo.columns and pd.notna(ultima_sessao.get("GROC_Label")):
            groc_label = str(ultima_sessao.get("GROC_Label"))

        if "PASS_Atingido" in df_evo.columns and pd.notna(ultima_sessao.get("PASS_Atingido")):
            val_pass = ultima_sessao.get("PASS_Atingido")
            if isinstance(val_pass, bool):
                pass_atingido = val_pass
            else:
                pass_atingido = str(val_pass).strip().lower() in ["true", "1", "sim", "yes"]

        if "PASS_Satisfacao" in df_evo.columns and pd.notna(ultima_sessao.get("PASS_Satisfacao")):
            pass_label = str(ultima_sessao.get("PASS_Satisfacao"))
            if pass_atingido is None:
                pass_atingido = pass_label.startswith("👍") or "sim" in pass_label.lower()

    distancia_meta = max(0.0, 100.0 - sane_atual)
    ganho_sane = sane_atual - sane_base

    if pass_atingido is True and (groc_score is not None and groc_score >= 3) and sane_atual >= 85:
        status = "meta_atingida"
        cor = "🟢"
        parecer = (
            f"Paciente atingiu Estado de Sintoma Aceitável (PASS = Sim), mudança global clinicamente "
            f"significativa (GROC {groc_score:+d} ≥ +3) e está a apenas {distancia_meta:.0f}% do seu objetivo final."
        )
    elif groc_score is not None and groc_score < 0:
        status = "alerta_insatisfacao"
        cor = "🔴"
        parecer = (
            f"Percepção de piora clínica relatada no GROC ({groc_score:+d} pts). "
            f"Reavaliar carga recente, expectativas e barreiras psicossociais."
        )
    elif pass_atingido is False and ganho_sane >= 15.0:
        status = "evoluindo_insatisfeito"
        cor = "🟡"
        parecer = (
            f"Ganho funcional relevante de +{ganho_sane:.0f}% no SANE (faltam {distancia_meta:.0f}% para a meta), "
            f"porém paciente ainda reporta PASS negativo (insatisfeito com o estado atual). Manter progressão."
        )
    else:
        status = "em_construcao"
        cor = "🔵"
        parecer = (
            f"Capacidade atual percebida (SANE) em {sane_atual:.0f}% (Δ {ganho_sane:+.0f}% vs Marco Zero). "
            f"Faltam {distancia_meta:.0f}% para atingir plenamente o objetivo funcional."
        )

    return {
        "objetivo": objetivo,
        "psfs_baseline": psfs_base,
        "sane_baseline": round(sane_base, 1),
        "sane_atual": round(sane_atual, 1),
        "ganho_sane": round(ganho_sane, 1),
        "distancia_meta": round(distancia_meta, 1),
        "groc_score": groc_score,
        "groc_label": groc_label,
        "pass_atingido": pass_atingido,
        "pass_label": pass_label,
        "status": status,
        "cor": cor,
        "parecer": parecer,
        "referencia": "Kamper 2009 (GROC) | Tubach 2005 (PASS) | Shelbourne 2009 (SANE) | Stratford 1995 (PSFS)"
    }


# ============================================================
# FUNÇÃO 4: Análise de Bandeiras (Compatível com Chaves Antigas e Novas)
# ============================================================
def analisar_bandeiras(avaliacao: dict) -> list:
    """
    Analisa a avaliação inicial e detecta bandeiras clínicas ativas
    (Vermelhas, Amarelas, Azuis e Negras).
    """
    bandeiras_ativas = []

    red_flags = _normalizar_lista_flags(
        avaliacao.get("Red_Flags") or avaliacao.get("Bandeiras_Vermelhas")
    )
    for flag in red_flags:
        bandeiras_ativas.append({
            "tipo": "vermelha",
            "cor": BANDEIRAS["vermelha"]["cor"],
            "gatilho": flag,
            "descricao": BANDEIRAS["vermelha"]["descricao"],
            "acao": BANDEIRAS["vermelha"]["acao"],
            "referencia": BANDEIRAS["vermelha"]["referencia"]
        })

    yellow_flags = _normalizar_lista_flags(
        avaliacao.get("Yellow_Flags") or avaliacao.get("Yellow_Cog") or avaliacao.get("Bandeiras_Amarelas")
    )
    for flag in yellow_flags:
        bandeiras_ativas.append({
            "tipo": "amarela",
            "cor": BANDEIRAS["amarela"]["cor"],
            "gatilho": flag,
            "descricao": BANDEIRAS["amarela"]["descricao"],
            "acao": BANDEIRAS["amarela"]["acao"],
            "referencia": BANDEIRAS["amarela"]["referencia"]
        })

    blue_black_raw = _normalizar_lista_flags(
        avaliacao.get("Blue_Flags") or avaliacao.get("Fatores_Sociais") or avaliacao.get("Bandeiras_Azuis")
    )
    termos_black_flag = ["inss", "litígio", "litigio", "processo", "judicial", "seguro", "afastado"]

    for flag in blue_black_raw:
        eh_negra = any(termo in flag.lower() for termo in termos_black_flag)
        tipo_chave = "negra" if eh_negra else "azul"
        bandeiras_ativas.append({
            "tipo": tipo_chave,
            "cor": BANDEIRAS[tipo_chave]["cor"],
            "gatilho": flag,
            "descricao": BANDEIRAS[tipo_chave]["descricao"],
            "acao": BANDEIRAS[tipo_chave]["acao"],
            "referencia": BANDEIRAS[tipo_chave]["referencia"]
        })

    dor_noturna = str(avaliacao.get("Dor_Noturna", "")).strip().lower()
    sono_aval = str(avaliacao.get("Sono", "")).strip().lower()
    if dor_noturna in ["sim", "s", "presente", "true", "yes"]:
        bandeiras_ativas.append({
            "tipo": "vermelha",
            "cor": BANDEIRAS["vermelha"]["cor"],
            "gatilho": "Dor noturna persistente relatada",
            "descricao": "Padrão inflamatório ou não-mecânico",
            "acao": "Considerar reavaliação médica",
            "referencia": "Greenhalgh 2006"
        })
    elif "acorda com dor" in sono_aval or "insônia" in sono_aval:
        bandeiras_ativas.append({
            "tipo": "amarela",
            "cor": BANDEIRAS["amarela"]["cor"],
            "gatilho": f"Alteração do Sono ({avaliacao.get('Sono')})",
            "descricao": "Privação de sono amplifica a sensibilização central e reduz modulação descendente da dor",
            "acao": "Higiene do sono e controle de carga inflamatória noturna",
            "referencia": "Finan 2013 (Sleep disturbance and pain — J Pain)"
        })

    return bandeiras_ativas


# ============================================================
# FUNÇÃO 5 (ORQUESTRADORA): analisar_paciente
# ============================================================
def analisar_paciente(paciente_nome: str) -> dict:
    """
    Função pública principal: recebe o nome do paciente, busca todos os dados
    no Firestore e retorna um dashboard clínico completo e auditável.
    """
    resultado = {
        "paciente": paciente_nome,
        "gerado_em": datetime.now().isoformat(),
        "fenotipo": None,
        "estagnacao": None,
        "estagnacao_funcional": None,
        "lsi": None,
        "percepcao_metas": None,
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
        else:
            resultado["fenotipo"] = normalizar_diagnostico("")
    except Exception:
        resultado["fenotipo"] = normalizar_diagnostico("")

    # --- 1. LEITURA DO HISTÓRICO (Evolucao) ---
    try:
        df_evo = conn.read_paciente("Evolucao", paciente_nome)
    except Exception:
        df_evo = pd.DataFrame()

    if not df_evo.empty:
        if "Data" in df_evo.columns:
            df_evo["_Data_dt"] = pd.to_datetime(df_evo["Data"], format="mixed", errors="coerce")
            df_evo = df_evo.sort_values("_Data_dt")

        resultado["sessoes_registradas"] = len(df_evo)

        if "Dor" in df_evo.columns:
            historico_dor = pd.to_numeric(df_evo["Dor"], errors="coerce").dropna().tolist()
            if historico_dor:
                resultado["estagnacao"] = analisar_estagnacao(historico_dor, "Dor")

    # --- 2. LEITURA DA AVALIAÇÃO (Avaliacao_Inicial) ---
    try:
        df_aval = conn.read_paciente("Avaliacao_Inicial", paciente_nome)
    except Exception:
        df_aval = pd.DataFrame()

    ultima_aval = {}
    if not df_aval.empty:
        if "Data_Avaliacao" in df_aval.columns:
            df_aval["_Data_dt"] = pd.to_datetime(df_aval["Data_Avaliacao"], format="mixed", dayfirst=True, errors="coerce")
            df_aval = df_aval.sort_values("_Data_dt")
        ultima_aval = df_aval.iloc[-1].to_dict()

        # --- Bandeiras ---
        resultado["bandeiras"] = analisar_bandeiras(ultima_aval)

        # --- LSI EXCLUSIVO POR DINAMOMETRIA ISOMÉTRICA (kgf) ---
        # Ignora completamente Forca_Geral_Dir/Esq (Escala de Oxford 0-5)
        ext_d = _extrair_valor_prefixo(ultima_aval.get("Dinamometria_Dir"), "Ext")
        ext_e = _extrair_valor_prefixo(ultima_aval.get("Dinamometria_Esq"), "Ext")
        fonte_lsi = "Dinamometria Quadríceps (kgf)"

        if ext_d > 0 or ext_e > 0:
            lado_ref = str(ultima_aval.get("Lado_Acometido", "")).lower()
            if "direito" in lado_ref or "dir > esq" in lado_ref:
                val_les, val_sau = ext_d, ext_e
            elif "esquerdo" in lado_ref or "esq > dir" in lado_ref:
                val_les, val_sau = ext_e, ext_d
            else:
                val_les, val_sau = min(ext_d, ext_e), max(ext_d, ext_e)

            if val_sau > 0:
                resultado["lsi"] = calcular_lsi(val_les, val_sau, fonte=fonte_lsi)
        elif "Dinamometria_Dir" not in ultima_aval and "Dinamometria_Esq" not in ultima_aval:
            # Retrocompatibilidade apenas para registros que tinham Forca_Lesado/Saudavel diretos sem string
            try:
                val_les = float(ultima_aval.get("Dinamometria_Lesado") or 0.0)
                val_sau = float(ultima_aval.get("Dinamometria_Saudavel") or 0.0)
            except (ValueError, TypeError):
                val_les, val_sau = 0.0, 0.0
            if val_sau > 5.0:  # > 5 kgf garante que não é grau de Oxford (0-5)
                resultado["lsi"] = calcular_lsi(val_les, val_sau, fonte=fonte_lsi)

        # --- Estagnação Funcional (SANE, LEFS ou KOOS se coletados no check-in) ---
        for score_func in ["SANE_Pct", "LEFS", "KOOS"]:
            if not df_evo.empty and score_func in df_evo.columns:
                hist = pd.to_numeric(df_evo[score_func], errors="coerce").dropna().tolist()
                if len(hist) >= SESSOES_MINIMAS_ESTAGNACAO:
                    chave_mcid = "SANE" if score_func == "SANE_Pct" else score_func
                    resultado["estagnacao_funcional"] = analisar_estagnacao(hist, chave_mcid)
                    break

    # --- 3. PERCEPÇÃO DE EVOLUÇÃO & METAS (PSFS, SANE, GROC, PASS) ---
    if ultima_aval or not df_evo.empty:
        resultado["percepcao_metas"] = analisar_percepcao_metas(ultima_aval, df_evo)

    return resultado


# ============================================================
# RENDERIZAÇÃO NO STREAMLIT (chamada pelo modulo_painel)
# ============================================================
def renderizar_insights(insights: dict, cores: dict):
    """
    Renderiza o dashboard de IA Clínica dentro da aba de Inteligência Clínica do Painel.
    """
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, {cores['primaria']} 0%, {cores['secundaria']} 100%);
                    padding: 20px; border-radius: 16px; color: white; margin-bottom: 20px;'>
            <h3 style='color: white; margin: 0;'>🧠 Insights Clínicos — IA Baseada em Evidência</h3>
            <p style='color: #E0F7FA; margin: 8px 0 0 0; font-size: 0.95rem;'>
                Análise determinística de estagnação (MCID), simetria bilateral por dinamometria (LSI), percepção de mudança (GROC/PASS) e bandeiras clínicas.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ==== FENÓTIPO CLÍNICO ====
    fen = insights.get("fenotipo") or {}
    if fen.get("fenotipo") and fen["fenotipo"] != "generico":
        st.markdown(
            f"<div style='background: {cores['fundo_claro']}; border-left: 4px solid {cores['secundaria']}; "
            f"padding: 12px 16px; border-radius: 8px; margin-bottom: 15px;'>"
            f"<strong style='color: {cores['primaria']};'>🎯 Fenótipo Clínico Identificado:</strong> {fen['label']}<br>"
            f"<small style='color: {cores['texto_suave']};'>Foco de análise: {', '.join(fen['metricas_relevantes'])} "
            f"| PROM principal: {fen['prom_principal']} "
            f"| Janela prognóstica PBE: {fen['tempo_esperado_semanas']} semanas</small>"
            f"</div>",
            unsafe_allow_html=True,
        )
    elif fen.get("fenotipo") == "generico":
        st.caption("ℹ️ Fenótipo específico não reconhecido no Cadastro. Padronize o Diagnóstico Clínico para ativar a janela prognóstica.")

    # ==== KPIs no topo ====
    pm = insights.get("percepcao_metas") or {}
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📅 Sessões Registradas", insights["sessoes_registradas"])
    with col2:
        n_bandeiras = len(insights["bandeiras"])
        st.metric("🚩 Bandeiras Ativas", n_bandeiras, delta=None if n_bandeiras == 0 else "Atenção", delta_color="inverse")
    with col3:
        if insights.get("lsi") and insights["lsi"].get("valor") is not None:
            st.metric(f"{insights['lsi']['cor']} LSI (Dinamometria)", f"{insights['lsi']['valor']}%")
        else:
            st.metric("📊 LSI (Dinamometria)", "N/D", help="Requer preenchimento da Dinamometria (kgf) na Avaliação Inicial")
    with col4:
        if pm.get("sane_atual") is not None:
            st.metric(
                "🎯 Distância da Meta",
                f"{pm['distancia_meta']:.0f}%",
                f"SANE Atual: {pm['sane_atual']:.0f}%"
            )
        else:
            st.metric("🎯 Distância da Meta", "N/D")

    st.markdown("---")

    # ==== 1. PERCEPÇÃO DO PACIENTE & METAS (GROC, PASS, SANE, PSFS) ====
    if pm:
        titulo("🧭 Alinhamento de Expectativa, Satisfação (PASS) & Objetivo (SANE/GROC)")
        st.markdown(f"**🏆 Objetivo Principal do Paciente:** *{pm.get('objetivo', 'Não informado')}*")

        c_pm1, c_pm2, c_pm3 = st.columns(3)
        c_pm1.metric(
            "Capacidade Atual (SANE)",
            f"{pm['sane_atual']:.0f}%",
            f"{pm['ganho_sane']:+.0f}% vs Marco Zero ({pm['sane_baseline']:.0f}%)"
        )
        c_pm2.metric(
            "Mudança Global (GROC)",
            f"{pm['groc_score']:+d} pts" if pm.get("groc_score") is not None else "N/D",
            pm.get("groc_label", "Sem registro")
        )
        c_pm3.metric(
            "Satisfação Atual (PASS)",
            "Satisfeito (Sim)" if pm.get("pass_atingido") is True else ("Insatisfeito (Não)" if pm.get("pass_atingido") is False else "N/D"),
            f"PSFS Inicial: {pm.get('psfs_baseline', '-')}/10"
        )

        if pm["status"] == "meta_atingida":
            st.success(f"{pm['cor']} **META FUNCIONAL E SATISFAÇÃO ATINGIDAS** — {pm['parecer']}")
        elif pm["status"] == "alerta_insatisfacao":
            st.error(f"{pm['cor']} **ALERTA DE PERCEPÇÃO NEGATIVA** — {pm['parecer']}")
        elif pm["status"] == "evoluindo_insatisfeito":
            st.warning(f"{pm['cor']} **EVOLUÇÃO EM CURSO (PASS AINDA NEGATIVO)** — {pm['parecer']}")
        else:
            st.info(f"{pm['cor']} **CONSTRUÇÃO FUNCIONAL** — {pm['parecer']}")
        st.caption(f"📚 Referências: {pm['referencia']}")
        st.markdown("---")

    # ==== 2. ESTAGNAÇÃO — DOR ====
    titulo("📉 Análise de Estagnação — Dor (EVA)")
    est = insights.get("estagnacao")

    if insights["sessoes_registradas"] == 0:
        st.info("ℹ️ Paciente ainda sem sessões de check-in registradas. Os cálculos longitudinais aparecerão após os primeiros atendimentos.")
    elif est is None or est.get("status") == "insuficiente":
        n_atual = est["sessoes_analisadas"] if est else insights["sessoes_registradas"]
        st.info(f"⏳ Aguardando dados: análise de estagnação requer ≥ {SESSOES_MINIMAS_ESTAGNACAO} sessões (há {n_atual}).")
    elif est["status"] == "estagnacao":
        st.warning(f"🟡 **ESTAGNAÇÃO DETECTADA**\n\n{est['racional']}")
        st.caption(f"📚 Referência: {est['referencia']}")
    elif est["status"] == "melhora":
        st.success(f"🟢 **EVOLUÇÃO POSITIVA**\n\n{est['racional']}")
        st.caption(f"📚 Referência: {est['referencia']}")
    elif est["status"] == "piora":
        st.error(f"🔴 **PIORA CLÍNICA**\n\n{est['racional']}")
        st.caption(f"📚 Referência: {est['referencia']}")

    # ==== 3. LSI (SOMENTE SE DINAMOMETRIA PREENCHIDA) ====
    if insights.get("lsi") and insights["lsi"].get("valor") is not None:
        st.markdown("---")
        titulo("⚖️ Limb Symmetry Index (LSI — Dinamometria Isométrica em kgf)")
        lsi_data = insights["lsi"]

        if lsi_data["classificacao"] == "alta_funcional":
            st.success(f"{lsi_data['cor']} **LSI {lsi_data['valor']}%** — {lsi_data['acao']}")
        elif lsi_data["classificacao"] == "atencao":
            st.warning(f"{lsi_data['cor']} **LSI {lsi_data['valor']}%** — {lsi_data['acao']}")
        else:
            st.error(f"{lsi_data['cor']} **LSI {lsi_data['valor']}%** — {lsi_data['acao']}")

        st.caption(f"📚 Referência: {lsi_data['referencia']}")

    # ==== 4. BANDEIRAS ====
    st.markdown("---")
    titulo("🚩 Bandeiras Clínicas Ativas (Triagem Biopsicossocial)")

    if not insights["bandeiras"]:
        st.success("✅ Nenhuma bandeira clínica ativa detectada. Perfil de baixo risco biopsicossocial.")
    else:
        for b in insights["bandeiras"]:
            if b["tipo"] == "vermelha":
                st.error(f"{b['cor']} **BANDEIRA VERMELHA** — {b['gatilho']}\n\n_{b['descricao']}_\n\n**Ação:** {b['acao']}")
            elif b["tipo"] == "amarela":
                st.warning(f"{b['cor']} **BANDEIRA AMARELA** — {b['gatilho']}\n\n_{b['descricao']}_\n\n**Ação:** {b['acao']}")
            elif b["tipo"] == "negra":
                st.error(f"{b['cor']} **BANDEIRA NEGRA (SISTÊMICA/LEGAL)** — {b['gatilho']}\n\n_{b['descricao']}_\n\n**Ação:** {b['acao']}")
            else:
                st.info(f"{b['cor']} **BANDEIRA {b['tipo'].upper()}** — {b['gatilho']}\n\n_{b['descricao']}_\n\n**Ação:** {b['acao']}")
            st.caption(f"📚 Referência: {b['referencia']}")
