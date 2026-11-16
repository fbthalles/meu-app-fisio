"""Convenções de leitura das medidas compartilhadas pelo painel e pelo laudo."""
from math import isfinite


def lados_dinamometria(direito, esquerdo, lado_acometido):
    lado = str(lado_acometido).lower()
    if "direito" in lado or "dir > esq" in lado:
        return direito, esquerdo
    if "esquerdo" in lado or "esq > dir" in lado:
        return esquerdo, direito
    return min(direito, esquerdo), max(direito, esquerdo)


def lsi_dinamometria(avaliado, referencia):
    # Nas fichas do GENUA, o campo de força não preenchido é salvo como zero.
    if all(isfinite(v) and v > 0 for v in (avaliado, referencia)):
        return round(avaliado / referencia * 100, 1)
    return None


def nota_dor_gesto(resposta, nota=None):
    categoria = str(resposta).strip()
    if categoria.startswith("Incapaz") or categoria in (
        "Não testado", "Não Aplicável (Fase Pós-Op)", "Dor não informada"
    ):
        return None
    try:
        valor = float(nota if nota is not None else resposta)
        if isfinite(valor):
            return min(10.0, max(0.0, valor))
    except (TypeError, ValueError):
        pass
    # Estimativas para fichas legadas que só guardavam a faixa de dor.
    return {
        "Sem Dor": 0, "Sem Dor (0)": 0,
        "Dor Leve": 2.5, "Dor Leve (1 - 3)": 2.5,
        "Dor Moderada": 5.5, "Dor Moderada (4 - 7)": 5.5,
        "Dor Grave": 8.5, "Dor Grave (8 - 10)": 8.5,
    }.get(categoria)


def pass_registrado(valor, descricao=None):
    """Mantém ausências/desconhecidos distintos de uma resposta negativa."""
    for item in (valor, descricao):
        texto = str(item).strip().lower()
        if texto in ('true', '1', '1.0', 'sim', 'yes') or texto.startswith(('👍', 'sim —')):
            return True
        if texto in ('false', '0', '0.0', 'não', 'nao', 'no') or texto.startswith(('👎', 'não —')):
            return False
    return None


def criterios_acompanhamento(dor, derrame, extensao_completa, flexao, lsi, sane, satisfacao):
    """Metas operacionais do MVP; None indica medida ausente, não falha clínica."""
    def limite(valor, minimo, maximo, alvo, maior=False):
        try:
            n = float(valor)
        except (TypeError, ValueError):
            return None
        if not isfinite(n) or not minimo <= n <= maximo:
            return None
        return bool(n >= alvo if maior else n <= alvo)
    sane_ok = limite(sane, 0, 100, 85, True)
    return (
        limite(dor, 0, 10, 2), limite(derrame, 0, 3, 1), extensao_completa,
        limite(flexao, 0, 180, 125, True), limite(lsi, 0, float('inf'), 90, True),
        bool(sane_ok and satisfacao) if sane_ok is not None and satisfacao is not None else None,
    )


def grau_derrame(valor):
    """Converte respostas reconhecidas para 0–3; desconhecidos ficam ausentes."""
    texto = str(valor).strip().lower()
    if texto in ("nenhum", "nenhuma", "ausente", "sem derrame"):
        return 0
    for grau, termos in [(3, ("+++", "intenso", "grave", "3+")), (2, ("++", "moderado", "2+")), (1, ("+", "leve", "vestígio", "onda"))]:
        if any(termo in texto for termo in termos):
            return grau
    try:
        numero = float(texto)
        if isfinite(numero) and numero.is_integer() and 0 <= numero <= 3:
            return int(numero)
    except (ValueError, TypeError):
        pass
    return float("nan")
