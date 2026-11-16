"""Regressions exercising the real form lifecycle against an in-memory database."""
import ast
import unittest
from clinical_source import tree, execute
from audit_support import State, MemoryDB
from services.patient_context import reiniciar_widgets_ficha, gravar_documento
from types import SimpleNamespace

class FormLifecycleTests(unittest.TestCase):
    def lifecycle(self, filename, state, choice, records=None):
        render=next(n for n in tree(filename).body if isinstance(n,ast.FunctionDef) and n.name=='render')
        start=next(i for i,n in enumerate(render.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id.startswith('trocou_escolha_') for t in n.targets))
        ns=dict(st=SimpleNamespace(session_state=state),escolha=choice,registros=records or {},reiniciar_widgets_ficha=reiniciar_widgets_ficha)
        execute(render.body[start:start+4], ns,filename)
        return ns

    def test_repeated_new_form_save_updates_same_document(self):
        for file,new,key,collection in [('modulo_avaliacao.py','➕ Nova Avaliação','doc_id_avaliacao','Avaliacao_Inicial'),('modulo_checkin.py','➕ Nova Sessão','doc_id_checkin','Evolucao')]:
            with self.subTest(file=file):
                state=State(paciente='Ficticio QA',_paciente_contexto='Ficticio QA')
                db=MemoryDB()
                self.lifecycle(file,state,new)
                gravar_documento(db,collection,state,key,{'Paciente':'Ficticio QA','Dor':4})
                first=state[key]
                self.lifecycle(file,state,new)
                gravar_documento(db,collection,state,key,{'Paciente':'Ficticio QA','Dor':2})
                self.assertEqual(state[key],first)
                self.assertEqual(len(db.records),1)
                self.assertEqual(db.records[collection,first]['Dor'],2)
                record={'id':first,'versao':db.versions[collection,first].rfc3339(),'data':db.records[collection,first]}
                self.lifecycle(file,state,first,{first:record})
                self.lifecycle(file,state,new)
                self.assertIsNone(state[key])

    def test_newly_saved_form_restores_payload_after_widget_cleanup(self):
        for file,new,key,payload_key in [('modulo_avaliacao.py','➕ Nova Avaliação','doc_id_avaliacao','_payload_avaliacao_atual'),('modulo_checkin.py','➕ Nova Sessão','doc_id_checkin','_payload_checkin_atual')]:
            state=State(paciente='Ficticio QA',_paciente_contexto='Ficticio QA')
            self.lifecycle(file,state,new)
            state[key]='saved-id'
            state[payload_key]={'Paciente':'Ficticio QA','Flexao':120,'Dor':4}
            ns=self.lifecycle(file,state,new)
            self.assertEqual(ns['dados']['Flexao'],120)
            self.assertEqual(ns['dados']['Dor'],4)


class ClinicalValidationTests(unittest.TestCase):
    def test_missing_measures_pending_and_zero_pain_is_valid(self):
        from services.medidas import criterios_acompanhamento
        self.assertEqual(criterios_acompanhamento(None,None,None,None,None,None,None),(None,)*6)
        self.assertEqual(criterios_acompanhamento(0,0,True,135,90,85,True),(True,)*6)
        self.assertEqual(criterios_acompanhamento(3,2,False,120,75,80,False),(False,)*6)
        self.assertIsNone(criterios_acompanhamento(0,0,True,135,None,85,None)[5])
        self.assertEqual(criterios_acompanhamento(float('nan'),None,None,None,None,None,None),(None,)*6)

    def test_pass_false_string_and_unknown_are_not_truthy(self):
        from services.medidas import pass_registrado
        for val in (False, 'false', 0, 'Não', '👎 Não'):
            self.assertIs(pass_registrado(val),False)
        for val in (None,float('nan'),'Não registrado','talvez'):
            self.assertIsNone(pass_registrado(val))
        self.assertIs(pass_registrado(None,'👍 Sim'),True)

    def test_sane_change_is_observed_without_fabricated_dates(self):
        import pandas as pd
        from clinical_source import load
        summary=load('modulo_painel.py')._resumir_evolucao_sane
        result=summary(pd.DataFrame({'SANE_Pct_Num':[30,None,85]}),30)
        self.assertEqual(result['delta'],55)
        self.assertTrue(pd.isna(result['real'][1]))
        self.assertNotIn('esperado',result)
        self.assertIn('pontos percentuais',result['resumo'])

    def test_unknown_effusion_is_not_a_normal_result(self):
        import math
        from clinical_source import load
        for filename,func in [('modulo_painel.py','_mapear_inchaco'),('pdf_laudo.py','_mapear_inchaco_grau')]:
            parse=getattr(load(filename),func)
            self.assertEqual(parse('Nenhum'),0)
            self.assertEqual(parse('Moderado (++)'),2)
            for value in [None,'Não avaliado',float('nan'),'2.5','4']:
                self.assertTrue(math.isnan(parse(value)))
