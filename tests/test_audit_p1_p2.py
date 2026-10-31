"""Audit only: expectedFailure reproduces open issues, never a clinical fix."""
import copy
import socket
import unittest
from unittest.mock import patch
import pandas as pd
from clinical_source import load
from audit_support import UI, MemoryDB, isolated, adapter_class, panel_longitudinal


class AuditP1P2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard = patch.object(socket, 'socket', side_effect=AssertionError('Network prohibited'))
        cls.guard.start()
        cls.addClassCleanup(cls.guard.stop)

    def test_required_bilateral_values_and_zero_denominator(self):
        ia = load('ia_clinica.py')
        r = ia.calcular_lsi(36,40,flex_lesado=24,flex_saudavel=30)
        self.assertEqual(r['valor'],90)
        self.assertAlmostEqual(24/40*100,60)
        self.assertEqual(ia.calcular_lsi(40,40,flex_lesado=24)['razao_iq_lesado'],60)
        self.assertIsNone(ia.calcular_lsi(36,0)['valor'])

    @unittest.expectedFailure
    def test_p1_01_zero_pain_does_not_imply_performed_test(self):
        self.assertIsNone(load('modulo_painel.py')._score_funcional_item('Não testado',dor_num_override=0))

    @unittest.expectedFailure
    def test_p1_02_absent_sane_is_not_observed_thirty(self):
        r = load('ia_clinica.py').analisar_percepcao_metas({},pd.DataFrame())
        self.assertIsNone(r['sane_atual'])

    def test_explicit_prom_not_applied_survives_legacy_values(self):
        record = {'PROMs_Aplicados':[], 'KOOS_Pct':100, 'LEFS_Pct':50}
        self.assertEqual(load('modulo_avaliacao.py')._detectar_proms_legados(record),[])
        self.assertEqual(load('modulo_painel.py')._detectar_proms_preenchidos(record),[])

    def test_five_sessions_different_dates_temporal_characterization(self):
        ia = load('ia_clinica.py')
        class Adapter:
            def read(self,collection): return pd.DataFrame([{'Nome':'Ficticio A'}])
            def read_paciente(self,collection,name):
                assert name == 'Ficticio A'
                if collection == 'Avaliacao_Inicial': return pd.DataFrame()
                return pd.DataFrame({'Data':self.dates, 'Dor':[4]*5})
        adapter = Adapter()
        ia.analisar_paciente.__globals__['conn'] = adapter
        results = []
        for frequency in ['h','30D']:
            adapter.dates = pd.date_range('2026-01-01',periods=5,freq=frequency).astype(str).tolist()
            results.append(ia.analisar_paciente('Ficticio A')['estagnacao'])
        self.assertEqual(results[0]['status'],'estagnacao')
        self.assertEqual(results[0]['status'],results[1]['status'])
        # Characterizes the absence of elapsed-time input, without inventing a cutoff.

    def test_checkin_two_consecutive_autosaves_same_payload(self):
        db = MemoryDB()
        ui = UI({'_payload_checkin_atual':{'Paciente':'Ficticio A','Dor':4},'autosave_checkin_ativo':True})
        mod = isolated('modulo_checkin.py',ui,db)
        mod._fragmento_autosave_checkin()
        mod._fragmento_autosave_checkin()
        self.assertEqual(len(db.records),1)
        self.assertEqual(len(db.writes),1)

    def test_assessment_two_consecutive_autosaves_same_payload(self):
        db = MemoryDB()
        ui = UI({'_payload_avaliacao_atual':{'Paciente':'Ficticio A','QP':'Queixa fictícia'}})
        mod = isolated('modulo_avaliacao.py',ui,db)
        mod._fragmento_autosave_avaliacao()
        mod._fragmento_autosave_avaliacao()
        self.assertEqual((len(db.records),len(db.writes)),(1,1))

    def test_edit_same_session_reuses_document(self):
        db = MemoryDB()
        ui = UI({'_payload_checkin_atual':{'Paciente':'Ficticio A','Dor':4},'autosave_checkin_ativo':True})
        mod = isolated('modulo_checkin.py',ui,db)
        mod._fragmento_autosave_checkin()
        ui.session_state['_payload_checkin_atual']['Dor'] = 2
        mod._fragmento_autosave_checkin()
        self.assertEqual(len(db.records),1)
        self.assertEqual(len(db.writes),2)
        self.assertEqual(next(iter(db.records.values()))['Dor'],2)

    @unittest.expectedFailure
    def test_p1_03_top_navigation_clears_previous_payload(self):
        ui = UI({'paciente':'Ficticio B','doc_id_avaliacao':'fake-a','_payload_avaliacao_atual':{'Paciente':'Ficticio A','QP':'Queixa A'},'qp':'Queixa A','sane_baseline':80})
        isolated('streamlit_app.py',ui)._limpar_estado_paciente_ativo()
        self.assertNotIn('_payload_avaliacao_atual',ui.session_state)
        self.assertNotIn('qp',ui.session_state)

    @unittest.expectedFailure
    def test_p1_04_patient_list_clears_checkin_payload(self):
        ui = UI({'_payload_checkin_atual':{'Paciente':'Ficticio A'},'autosave_checkin_ativo':True})
        isolated('ui_dados_paciente.py',ui)._limpar_contexto_paciente_anterior()
        self.assertNotIn('_payload_checkin_atual',ui.session_state)
        self.assertFalse(ui.session_state.get('autosave_checkin_ativo',False))

    @unittest.expectedFailure
    def test_p1_05_recovery_without_new_draft_must_clear_old_data(self):
        ui = UI()
        mod = isolated('services/session_resilience.py',ui)
        mod.inicializar_estado_avaliacao('draft_fake_A')
        mod.atualizar_campo('Paciente','Ficticio A')
        mod.inicializar_estado_avaliacao('draft_fake_B',MemoryDB())
        self.assertEqual(ui.session_state['avaliacao_atual'],{})

    def test_recovery_loads_existing_fake_draft(self):
        db = MemoryDB()
        db.collection('avaliacoes_rascunho').document('draft_fake_A').set({'dados':{'Paciente':'Ficticio A','QP':'Fictícia'}})
        ui = UI()
        isolated('services/session_resilience.py',ui).inicializar_estado_avaliacao('draft_fake_A',db)
        self.assertEqual(ui.session_state['avaliacao_atual']['QP'],'Fictícia')

    @unittest.expectedFailure
    def test_p1_06_retry_after_lost_ack_does_not_duplicate(self):
        db = MemoryDB()
        db.timeout_after_add = True
        ui = UI({'_payload_checkin_atual':{'Paciente':'Ficticio A','Data':'2026-01-01'},'autosave_checkin_ativo':True})
        mod = isolated('modulo_checkin.py',ui,db)
        mod._fragmento_autosave_checkin()
        mod._fragmento_autosave_checkin()
        self.assertEqual(len(db.records),1)

    @unittest.expectedFailure
    def test_p1_07_two_clients_same_logical_session_do_not_duplicate(self):
        db = MemoryDB()
        for _ in range(2):
            ui = UI({'_payload_checkin_atual':{'Paciente':'Ficticio A','Data':'2026-01-01','Sessao_ID':'fake-same-session'},'autosave_checkin_ativo':True})
            isolated('modulo_checkin.py',ui,db)._fragmento_autosave_checkin()
        self.assertEqual(len(db.records),1)

    def test_failed_write_does_not_mark_hash_saved(self):
        db = MemoryDB()
        db.fail_writes = True
        ui = UI({'_payload_checkin_atual':{'Paciente':'Ficticio A'},'autosave_checkin_ativo':True})
        isolated('modulo_checkin.py',ui,db)._fragmento_autosave_checkin()
        self.assertNotIn('_ultimo_hash_autosave_chk',ui.session_state)
        self.assertEqual(len(db.records),0)

    @unittest.expectedFailure
    def test_p1_08_failed_write_must_not_show_stale_green_status(self):
        db = MemoryDB()
        db.fail_writes = True
        ui = UI({'_payload_checkin_atual':{'Paciente':'Ficticio A'},'autosave_checkin_ativo':True,'_horario_autosave_chk':'12:00:00'})
        isolated('modulo_checkin.py',ui,db)._fragmento_autosave_checkin()
        self.assertFalse(any('🟢' in message for message in ui.messages))

    def test_legacy_parsers_are_read_only_and_accept_existing_formats(self):
        check = isolated('modulo_checkin.py')
        panel = load('modulo_painel.py')
        record={'Dinamometria_Dir':'Ext:36,0 | Flex:24,0','Data':'01/02/2026','Agachamento':'Dor Moderada (4 - 7)'}
        before=copy.deepcopy(record)
        self.assertEqual(panel._extrair_chave_str(record['Dinamometria_Dir'],'Ext'),36)
        self.assertEqual(check._parse_data_segura(record['Data']).month,2)
        self.assertEqual(check._categoria_antiga_para_dor_num(record['Agachamento']),(5,False))
        self.assertEqual(record,before)

    @unittest.expectedFailure
    def test_p1_09_legacy_not_tested_must_not_become_zero_pain(self):
        self.assertIsNone(isolated('modulo_checkin.py')._categoria_antiga_para_dor_num('Não testado')[0])

    @unittest.expectedFailure
    def test_p1_10_no_tests_must_not_be_full_bilateral_symmetry(self):
        result = panel_longitudinal(pd.DataFrame([{'Data':'2026-01-01','Dor':0,'Testes_Funcionais':{}}]))
        self.assertTrue(pd.isna(result.iloc[0]['LSI']))

    def test_longitudinal_dates_sorted_with_legacy_records(self):
        result=panel_longitudinal(pd.DataFrame([{'Data':'2026-01-02','Dor':3},{'Data':'2026-01-01','Dor':5}]))
        self.assertEqual(result['Dor'].tolist(),[5,3])

    @unittest.expectedFailure
    def test_p1_11_adapter_repeated_session_write_is_idempotent(self):
        db=MemoryDB()
        adapter=adapter_class()
        adapter.update.__globals__.update(db=db,invalidar_cache=lambda *args:None)
        frame=pd.DataFrame([{'Paciente':'Ficticio A','Sessao_ID':'same-fake-id','Dor':2}])
        adapter().update('Evolucao',frame)
        adapter().update('Evolucao',frame)
        self.assertEqual(len(db.records),1)

    @unittest.expectedFailure
    def test_p1_12_brazilian_dates_keep_calendar_order(self):
        result=panel_longitudinal(pd.DataFrame([{'Data':'02/01/2026','Dor':2},{'Data':'01/02/2026','Dor':5}]))
        self.assertEqual(result['Dor'].tolist(),[2,5])

    @unittest.expectedFailure
    def test_p1_13_missing_pain_is_not_zero(self):
        result=panel_longitudinal(pd.DataFrame([{'Data':'2026-01-01'}]))
        self.assertTrue(pd.isna(result.iloc[0]['Dor']))

    @unittest.expectedFailure
    def test_p1_14_stale_patient_payload_is_not_saved_after_switch(self):
        db=MemoryDB()
        ui=UI({'paciente':'Ficticio B','doc_id_avaliacao':'fake-A','_payload_avaliacao_atual':{'Paciente':'Ficticio A','QP':'Queixa fictícia'}})
        isolated('streamlit_app.py',ui,db)._limpar_estado_paciente_ativo()
        isolated('modulo_avaliacao.py',ui,db)._fragmento_autosave_avaliacao()
        self.assertEqual(db.records,{})

    @unittest.expectedFailure
    def test_p1_15_stale_client_must_not_silently_overwrite_recent_save(self):
        db=MemoryDB()
        for pain in [2,8]:  # recent value followed by stale second-client payload
            ui=UI({'doc_id_checkin':'same-fake-document','autosave_checkin_ativo':True,'_payload_checkin_atual':{'Paciente':'Ficticio A','Dor':pain}})
            isolated('modulo_checkin.py',ui,db)._fragmento_autosave_checkin()
        self.assertEqual(db.records[('Evolucao','same-fake-document')]['Dor'],2)

    def test_characterize_prognostic_real_series_imputes_missing_sane(self):
        df=pd.DataFrame({'Data_dt':pd.to_datetime(['2026-01-01']),'Sessão_Num':['S1'],'SANE_Pct_Num':[float('nan')]})
        result=load('modulo_painel.py')._calcular_curva_prognostica_sane(df,df,30)
        self.assertEqual(result['real'],[30])
        self.assertEqual(result['real_atual'],30)

    def test_service_draft_hash_avoids_redundant_writes(self):
        db=MemoryDB()
        ui=UI({'avaliacao_id':'draft_fake_A','avaliacao_atual':{'QP':'Fictícia'}})
        mod=isolated('services/session_resilience.py',ui)
        mod.monitor_autosave_firestore(db)
        mod.monitor_autosave_firestore(db)
        self.assertEqual(len(db.writes),1)
