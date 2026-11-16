import unittest
from types import SimpleNamespace
from unittest.mock import patch
from audit_support import State
import routing

class NavigationTests(unittest.TestCase):
    def test_list_reload_does_not_reopen_previous_patient(self):
        query={'auth':routing.codificar_sessao_url('qa@example.invalid'),'pac':'Ficticio anterior','mod':'Painel Analítico 📊'}
        ui=SimpleNamespace(query_params=query,session_state=State(user_email='qa@example.invalid',pagina='dados_paciente',paciente=None,modulo_ativo='Painel Analítico 📊'))
        with patch.object(routing,'st',ui):
            routing.aplicar_roteamento()
            self.assertNotIn('pac',query)
            self.assertNotIn('mod',query)
            ui.session_state=State()
            routing.aplicar_roteamento()
            self.assertEqual(ui.session_state.pagina,'dados_paciente')

    def test_active_patient_survives_reload(self):
        query={'auth':routing.codificar_sessao_url('qa@example.invalid'),'pac':'Ficticio A','mod':'Check-in Diário 📝'}
        ui=SimpleNamespace(query_params=query,session_state=State())
        with patch.object(routing,'st',ui):
            routing.aplicar_roteamento()
            self.assertEqual(ui.session_state.paciente,'Ficticio A')
            self.assertEqual(ui.session_state.modulo_ativo,'Check-in Diário 📝')
