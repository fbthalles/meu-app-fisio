"""Regression of the first P1 fix package, using synthetic patient contexts only."""
import ast
import socket
import unittest
from unittest.mock import patch
from services.patient_context import limpar_contexto_paciente, preparar_contexto_paciente, payload_do_paciente_ativo
from audit_support import UI, MemoryDB, isolated
from clinical_source import tree


class PatientContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original_socket = socket.socket
        def unix_only(family=socket.AF_INET, *args, **kwargs):
            if family != socket.AF_UNIX:
                raise AssertionError('Network prohibited')
            return original_socket(family, *args, **kwargs)
        # AppTest's asyncio loop uses a local UNIX socketpair, never TCP/IP.
        guard=patch.object(socket,'socket',side_effect=unix_only)
        guard.start()
        cls.addClassCleanup(guard.stop)

    def test_cleanup_preserves_auth_and_navigation_only(self):
        state=dict(user_email='ficticio@example.invalid',autenticado=True,pagina='painel_clinico',paciente='Ficticio A',modulo_ativo='Check-in',membro_ativo='Joelho',paciente_alvo=False)
        expected=state.copy()
        state.update(doc_id_checkin='fake-a',_payload_avaliacao_atual={'Paciente':'Ficticio A'},_ultimo_hash_autosave_chk='old',slider_groc_7=7,new_unknown_clinical_widget='old',**{'$$ID-fake-unkeyed-widget':123})
        limpar_contexto_paciente(state)
        self.assertEqual(state,expected)

    def test_a_b_a_discards_widgets_and_payloads(self):
        state={'paciente':'Ficticio A','autenticado':True}
        for name in ['Ficticio A','Ficticio B','Ficticio A']:
            state['paciente']=name
            preparar_contexto_paciente(state)
            self.assertNotIn('doc_id_avaliacao',state)
            self.assertNotIn('lefs_0',state)
            self.assertEqual(state['_paciente_contexto'],name)
            state.update(doc_id_avaliacao='fake-'+name,lefs_0='resposta fictícia')

    def test_same_patient_rerun_preserves_unsaved_inputs(self):
        state={'paciente':'Ficticio A'}
        preparar_contexto_paciente(state)
        state.update(lefs_0='resposta fictícia',_payload_checkin_atual={'Paciente':'Ficticio A'})
        before=state.copy()
        preparar_contexto_paciente(state)
        self.assertEqual(state,before)

    def test_missing_or_mismatched_patient_rejects_payload(self):
        for state in [{},{'paciente':''},{'paciente':'Ficticio B'},{'paciente':'Ficticio A','_paciente_contexto':'Ficticio B'}]:
            self.assertFalse(payload_do_paciente_ativo({'Paciente':'Ficticio A'},state))
        self.assertTrue(payload_do_paciente_ativo({'Paciente':'Ficticio A'},{'paciente':'Ficticio A'}))
        self.assertFalse(payload_do_paciente_ativo(None,{'paciente':'Ficticio A'}))

    def test_both_fragments_block_stale_and_missing_context(self):
        for filename,func,key in [('modulo_checkin.py','_fragmento_autosave_checkin','_payload_checkin_atual'),('modulo_avaliacao.py','_fragmento_autosave_avaliacao','_payload_avaliacao_atual')]:
            for active in [None,'Ficticio B']:
                with self.subTest(filename=filename,active=active):
                    db=MemoryDB()
                    ui=UI({'paciente':active,key:{'Paciente':'Ficticio A','QP':'Queixa fictícia'},'autosave_checkin_ativo':True,'doc_id_checkin':'existing-fake-id','doc_id_avaliacao':'existing-fake-id'})
                    getattr(isolated(filename,ui,db),func)()
                    self.assertEqual(db.writes,[])
                    self.assertTrue(any('bloqueado' in m for m in ui.messages))

    def test_existing_patient_document_preserved_while_other_patient_saved(self):
        db=MemoryDB()
        db.collection('Avaliacao_Inicial').document('fake-a').set({'Paciente':'Ficticio A','QP':'Histórico fictício A'})
        ui=UI({'paciente':'Ficticio B','doc_id_avaliacao':'fake-a','_paciente_contexto':'Ficticio A'})
        preparar_contexto_paciente(ui.session_state)
        ui.session_state['_payload_avaliacao_atual']={'Paciente':'Ficticio B','QP':'Queixa fictícia B'}
        isolated('modulo_avaliacao.py',ui,db)._fragmento_autosave_avaliacao()
        self.assertEqual(db.records[('Avaliacao_Inicial','fake-a')],{'Paciente':'Ficticio A','QP':'Histórico fictício A'})
        self.assertEqual(len(db.records),2)
        self.assertEqual(db.records[('Avaliacao_Inicial',ui.session_state['doc_id_avaliacao'])]['Paciente'],'Ficticio B')

    def test_manual_paths_have_context_guard_before_write(self):
        # Protect wiring in the UI without running Firebase or the full clinical form.
        for filename,payload in [('modulo_checkin.py','dados_sessao'),('modulo_avaliacao.py','dados_avaliacao')]:
            render=next(n for n in tree(filename).body if isinstance(n,ast.FunctionDef) and n.name=='render')
            guards=[n for n in ast.walk(render) if isinstance(n,ast.If) and isinstance(n.test,ast.UnaryOp) and isinstance(n.test.operand,ast.Call) and isinstance(n.test.operand.func,ast.Name) and n.test.operand.func.id=='payload_do_paciente_ativo']
            self.assertEqual(len(guards),1)
            self.assertEqual(guards[0].test.operand.args[0].id,payload)
            self.assertTrue(any(isinstance(n,ast.Return) for n in guards[0].body))

    def test_failed_draft_recovery_does_not_reuse_other_patient_data(self):
        class UnavailableDB:
            def collection(self,*args): raise ConnectionError('Synthetic offline')
        ui=UI({'avaliacao_id':'draft_fake_A','avaliacao_atual':{'Paciente':'Ficticio A'}})
        isolated('services/session_resilience.py',ui).inicializar_estado_avaliacao('draft_fake_B',UnavailableDB())
        self.assertEqual(ui.session_state['avaliacao_atual'],{})

    def test_real_streamlit_widgets_reset_on_switch_and_persist_on_rerun(self):
        from streamlit.testing.v1 import AppTest
        script = '''
import streamlit as st
from services.patient_context import preparar_contexto_paciente, limpar_contexto_paciente, chave_widget
st.session_state.setdefault('paciente','Ficticio A')
preparar_contexto_paciente(st.session_state)
st.text_input('Queixa fictícia',key='queixa')
st.text_input('Observação fictícia sem chave original',key=chave_widget(st.session_state,'observacao'))
def trocar():
    limpar_contexto_paciente(st.session_state)
    st.session_state['paciente'] = 'Ficticio B'
st.button('Trocar paciente',on_click=trocar)
st.caption(st.session_state['paciente'])
'''
        app=AppTest.from_string(script).run(timeout=20)
        self.assertEqual(len(app.exception),0)
        app.text_input[0].input('Queixa A').run()
        app.text_input[1].input('Observação A').run()
        app.run()
        self.assertEqual([w.value for w in app.text_input],['Queixa A','Observação A'])
        app.button[0].click().run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual([w.value for w in app.text_input],['',''])
        self.assertEqual(app.session_state['paciente'],'Ficticio B')

    def test_clinical_inputs_have_explicit_widget_keys(self):
        widgets={'text_input','text_area','slider','number_input','selectbox','radio','multiselect','checkbox','date_input','time_input','select_slider','pills','toggle','segmented_control'}
        for filename in ['modulo_avaliacao.py','modulo_checkin.py']:
            render=next(n for n in tree(filename).body if isinstance(n,ast.FunctionDef) and n.name=='render')
            calls=[n for n in ast.walk(render) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in widgets]
            self.assertGreater(len(calls),0)
            for node in calls:
                with self.subTest(filename=filename,line=node.lineno):
                    self.assertTrue(any(k.arg=='key' for k in node.keywords))
