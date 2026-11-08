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
