import unittest
from pdf_laudo import gerar_laudo_html


class LaudoTest(unittest.TestCase):
    def test_medidas_ausentes_e_forca_unilateral(self):
        for ausente in [None, float("nan"), ""]:
            with self.subTest(ausente=ausente):
                html = gerar_laudo_html("Teste", {"Dinamometria_Dir": "Ext:36"}, [
                    {"Data": "2026-10-01", "Dor": 8},
                    {"Data": "2026-10-02", "Dor": ausente},
                ])
                self.assertIn("LSI indisponível (medida unilateral)", html)
                self.assertIn("Dados insuficientes para resumir a evolução", html)
                self.assertNotIn("0/10 na EVA", html)

    def test_zero_medido_e_forca_bilateral(self):
        html = gerar_laudo_html("Teste", {
            "Dinamometria_Dir": "Ext:30", "Dinamometria_Esq": "Ext:40"
        }, [{"Data": "2026-10-01", "Dor": 0}])
        self.assertIn("Atual: 0/10 na EVA", html)
        self.assertIn("LSI Dinamometria: 75%", html)

    def test_adm_e_dor_usam_sessao_em_ordem_cronologica(self):
        historico = [
            {"Data": "01/11/2026", "Flexao": 90, "Extensao": "Déficit de -5°",
             "Testes_Funcionais": {"Afundo": "Dor Leve"}, "Testes_Funcionais_Dor_Num": {"Afundo": 2}},
            {"Data": "2026-10-31", "Flexao": 135, "Extensao": "Completa (0°)",
             "Testes_Funcionais": {"Afundo": "Dor Moderada"}, "Testes_Funcionais_Dor_Num": {"Afundo": 4}},
        ]
        html = gerar_laudo_html("Teste", {}, historico)
        self.assertIn('aria-label="90 graus · Referência 135°"', html)
        self.assertIn('aria-label="5 graus · Déficit de extensão"', html)
        self.assertIn("Afundo: dor de 4/10 em S1 (31/10) e 2/10 em S2 (01/11)", html)
        self.assertNotIn("Melhora clínica significativa", html)

    def test_lsi_acima_de_cem_preserva_o_lado_de_referencia(self):
        for lado, dir_kg, esq_kg in [("Direito", 45, 40), ("Esquerdo", 40, 45)]:
            with self.subTest(lado=lado):
                html = gerar_laudo_html("Teste", {"Lado_Acometido": lado,
                    "Dinamometria_Dir": f"Ext:{dir_kg}", "Dinamometria_Esq": f"Ext:{esq_kg}"}, [])
                self.assertIn("LSI Dinamometria: 112.5%", html)
                self.assertIn("Maior força no lado acometido", html)

    def test_teste_nao_realizado_nao_gera_nota_no_laudo(self):
        html = gerar_laudo_html("Teste", {}, [{"Data": "2026-11-01",
            "Testes_Funcionais": {"Afundo": "Incapaz", "Salto": "Não testado"},
            "Testes_Funcionais_Dor_Num": {"Afundo": 10, "Salto": 0}}])
        self.assertFalse('alt="Testes Funcionais"' in html)
