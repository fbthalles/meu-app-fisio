"""Synthetic-only calculation tests. Run: python -m unittest discover -s tests -v."""
import copy
import unittest
from unittest.mock import patch
import socket
import pandas as pd
from clinical_source import load, questionnaire, evaluation_assignment


class ClinicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # All sockets prohibited, including accidental access through future edits.
        cls.guard = patch.object(socket, 'socket', side_effect=AssertionError('Network forbidden in clinical tests'))
        cls.guard.start()
        cls.addClassCleanup(cls.guard.stop)
        cls.ia = load('ia_clinica.py')
        cls.panel = load('modulo_painel.py')
        cls.av = load('modulo_avaliacao.py')

    def test_lsi_exact_values_thresholds_and_over_100(self):
        for force, expected, category in [(0, 0, 'risco'), (84.9, 84.9, 'risco'), (85, 85, 'atencao'), (89.9, 89.9, 'atencao'), (90, 90, 'alta_funcional'), (120, 120, 'alta_funcional')]:
            with self.subTest(force=force):
                r = self.ia.calcular_lsi(force, 100)
                self.assertEqual((r['valor'], r['classificacao']), (expected, category))

    def test_iq_and_hamstring_lsi(self):
        r = self.ia.calcular_lsi(40, 50, flex_lesado=24, flex_saudavel=30)
        self.assertEqual([r[k] for k in ('valor', 'lsi_isquios', 'razao_iq_lesado', 'razao_iq_saudavel')], [80, 80, 60, 60])

    def test_lsi_invalid_denominators_and_missing(self):
        for a, b in [(None, 40), (40, None), (40, 0), (40, -1), (-1, 40)]:
            with self.subTest(a=a, b=b):
                self.assertIsNone(self.ia.calcular_lsi(a, b)['valor'])

    def test_panel_laterality_and_consistency(self):
        for side, d, e, expected in [('Direito', 36, 40, 90), ('Esquerdo', 40, 36, 90), ('Bilateral', 40, 36, 90), ('Direito', 48, 40, 120)]:
            with self.subTest(side=side):
                result = self.panel._calcular_lsi_seguro(d, e, side)
                self.assertEqual(result[0], expected)
                self.assertEqual(result[0], self.ia.calcular_lsi(result[1], result[2])['valor'])
        self.assertIsNone(self.panel._calcular_lsi_seguro(40, 0, 'Direito')[0])

    def test_no_flexion_measurement_is_not_ratio_zero(self):
        r = self.ia.calcular_lsi(40, 50)
        for k in ['lsi_isquios', 'razao_iq_lesado', 'razao_iq_saudavel']:
            self.assertIsNone(r[k])

    def test_stagnation_window_direction_and_threshold(self):
        for score, history, status, delta in [('Dor', [8,8,7,7,6], 'melhora', 2), ('Dor', [6,7,7,8,8], 'piora', -2), ('Dor', [6]*5, 'estagnacao', 0), ('LEFS', [20,22,24,26,29], 'melhora', 9), ('SANE', [30,30,30,30,44], 'estagnacao', 14), ('SANE', [30,30,30,30,45], 'melhora', 15)]:
            with self.subTest(score=score, history=history):
                r = self.ia.analisar_estagnacao([999] + history, score)
                self.assertEqual((r['status'], r['delta'], r['sessoes_analisadas']), (status, delta, 5))
        self.assertEqual(self.ia.analisar_estagnacao([], 'Dor')['status'], 'insuficiente')
        self.assertEqual(self.ia.analisar_estagnacao([1]*5, 'unknown')['status'], 'indefinido')

    def test_sane_groc_and_pass(self):
        for groc, sane, satisfied, status in [(3,85,True,'meta_atingida'),(-1,90,True,'alerta_insatisfacao'),(0,50,False,'evoluindo_insatisfeito'),(2,85,True,'em_construcao')]:
            with self.subTest(groc=groc):
                r = self.ia.analisar_percepcao_metas({'SANE_Baseline_Pct':30}, pd.DataFrame([dict(SANE_Pct=sane,GROC_Score=groc,PASS_Atingido=satisfied)]))
                self.assertEqual(r['status'],status)
                self.assertEqual(r['ganho_sane'],sane-30)
                self.assertEqual(r['distancia_meta'],100-sane)

    def test_perception_missing_and_malformed(self):
        for value in [None, float('nan'), 'inválido']:
            r=self.ia.analisar_percepcao_metas({'SANE_Baseline_Pct':40},pd.DataFrame([dict(SANE_Pct=value,GROC_Score=value)]))
            self.assertEqual(r['sane_atual'],40)
            self.assertIsNone(r['groc_score'])
        self.assertEqual(self.ia.analisar_percepcao_metas({},pd.DataFrame())['sane_baseline'],30)

    def test_functional_item_missing_and_clamping(self):
        for response, override, expected in [(None,None,None),('Não testado',None,None),('Sem Dor',None,10),('Dor Moderada',None,4.5),('Incapaz',None,0),(7,None,3),('Dor Grave',2,8),(None,20,0),(None,-2,10)]:
            with self.subTest(response=response,override=override):
                self.assertEqual(self.panel._score_funcional_item(response,override),expected)

    def test_proms_explicit_metadata_preserves_zero(self):
        d={'PROMs_Aplicados':['LEFS','KOOS'],'LEFS_Pct':0,'KOOS_Pct':0}
        self.assertEqual(self.av._detectar_proms_legados(d),['LEFS','KOOS'])
        self.assertEqual(self.panel._detectar_proms_preenchidos(d),['LEFS','KOOS'])

    def test_lefs_endpoints_midpoint_and_equivalent_points(self):
        for answer,pct,points in [('Incapaz / Extrema Dificuldade',0,0),('Dificuldade Moderada',50,40),('Nenhuma Dificuldade',100,80)]:
            r=questionnaire('LEFS (',{f'lefs_{i}':answer for i in range(10)})
            self.assertEqual((r['pct_lefs_calc'],r['pts_lefs_80_calc']),(pct,points))
            self.assertEqual(len(r['novas_respostas_proms']),10)

    def test_koos_endpoints_midpoint(self):
        for answer,expected in [('Extremo / Sempre (0)',0),('Moderado (2)',50),('Nenhum / Nunca (4)',100)]:
            r=questionnaire('KOOS-12 /',{f'k{i}':answer for i in range(1,13)})
            self.assertEqual(r['pct_koos_calc'],expected)
            self.assertEqual(len(r['novas_respostas_proms']),12)

    def test_womac_endpoints_midpoint(self):
        r=questionnaire('Índice WOMAC',{})
        keys=r['novas_respostas_proms']
        self.assertEqual(len(keys),15)
        for answer,expected in [('Nenhuma',100),('Moderada',50),('Muito Intensa',0)]:
            self.assertEqual(questionnaire('Índice WOMAC',dict.fromkeys(keys,answer))['pct_womac_calc'],expected)

    def test_lysholm_endpoints(self):
        r=questionnaire('Lysholm Completa',{})
        self.assertEqual(r['score_lysholm_calc'],100)
        worst={f'ly{i}':r[key][-1] for i,key in enumerate(['op_ly_mancar','op_ly_apoio','op_ly_trav','op_ly_inst','op_ly_dor','op_ly_inc','op_ly_esc','op_ly_aga'],1)}
        self.assertEqual(questionnaire('Lysholm Completa',worst)['score_lysholm_calc'],0)

    def test_bug_ikdc_best_responses_should_sum_100(self):
        r=questionnaire('IKDC Subjetivo',dict(ik1=10,ik2='Nenhuma (10 pts)',ik_at='Esporte Intenso / Corte e Giro (10 pts)',ik4=10))
        self.assertEqual(r['score_ikdc_calc'],100)

    def test_bug_visap_best_responses_should_sum_100(self):
        r=questionnaire('VISA-P Completo',{**{f'vp{i}':10 for i in range(1,7)},'vp7':'Competindo no mesmo nível ou maior (10 pts)','vp8':'Treina sem nenhuma dor (30 pts)'})
        self.assertEqual(r['score_visap_calc'],100)

    def test_visap_intermediate_and_worst(self):
        r=questionnaire('VISA-P Completo',{**{f'vp{i}':5 for i in range(1,7)},'vp7':'Treino modificado (4 pts)','vp8':'Treina com dor suportável (15 pts)'})
        self.assertEqual(r['score_visap_calc'],49)
        self.assertEqual(questionnaire('VISA-P Completo',{f'vp{i}':0 for i in range(1,7)})['score_visap_calc'],0)

    def test_bug_sane_zero_baseline_must_remain_zero(self):
        r=self.ia.analisar_percepcao_metas({'SANE_Baseline_Pct':0},pd.DataFrame([{'SANE_Pct':20}]))
        self.assertEqual((r['sane_baseline'],r['ganho_sane']),(0,20))

    def test_bug_nan_lsi_must_be_unavailable(self):
        self.assertIsNone(self.ia.calcular_lsi(float('nan'),40)['valor'])

    def test_bug_none_flexion_must_not_crash(self):
        self.assertIsNone(self.ia.calcular_lsi(40,50,flex_lesado=None,flex_saudavel=30)['lsi_isquios'])

    def test_bug_missing_history_must_not_look_like_deterioration(self):
        self.assertNotEqual(self.ia.analisar_estagnacao([float('nan')]*5,'Dor')['status'],'piora')

    def test_bug_explicit_empty_proms_should_be_consistent(self):
        d={'PROMs_Aplicados':[],'LEFS_Pct':50}
        self.assertEqual(self.av._detectar_proms_legados(d),self.panel._detectar_proms_preenchidos(d))

    def test_evaluation_inline_lsi_and_iq(self):
        self.assertEqual(evaluation_assignment('lsi_g',lesado=36,saudavel=40),90)
        self.assertEqual(evaluation_assignment('iq_dir',din_flex_d=24,din_ext_d=40),60)
        self.assertEqual(evaluation_assignment('iq_esq',din_flex_e=30,din_ext_e=50),60)
        self.assertIsNone(evaluation_assignment('iq_dir',din_flex_d=24,din_ext_d=0))

    def test_zero_denominator_consistent_between_screens(self):
        self.assertIsNone(evaluation_assignment('lsi_g',lesado=40,saudavel=0))
        self.assertIsNone(self.panel._calcular_lsi_seguro(40,0,'Direito')[0])

    def test_characterize_iq_threshold_disagreement(self):
        label=evaluation_assignment('status_iq_d',iq_dir=69)
        self.assertIn('Ideal',label)
        self.assertIn('elevada',self.ia.calcular_lsi(100,100,flex_lesado=69)['acao'])

    def test_ikdc_intermediate_and_worst(self):
        r=questionnaire('IKDC Subjetivo',dict(ik1=5,ik2='Diária (2 pts)',ik_at='Atividades Leves (3 pts)',ik4=5))
        self.assertEqual(r['score_ikdc_calc'],40)
        r=questionnaire('IKDC Subjetivo',dict(ik1=0,ik2='Constante (0 pts)',ik_at='Incapaz (0 pts)',ik4=0))
        self.assertEqual(r['score_ikdc_calc'],0)

    def test_bug_groc_outside_scale_should_not_enable_goal(self):
        r=self.ia.analisar_percepcao_metas({},pd.DataFrame([dict(SANE_Pct=90,GROC_Score=99,PASS_Atingido=True)]))
        self.assertNotEqual(r['status'],'meta_atingida')

    def test_groc_requires_integer_within_scale(self):
        for value in [None, 'invalid', float('nan'), float('inf'), -8, 8, 3.5]:
            with self.subTest(value=value):
                self.assertIsNone(self.ia._groc_valido(value))
        for value in [-7, 0, 7, '3']:
            self.assertEqual(self.ia._groc_valido(value),int(value))

    def test_sane_zero_and_invalid_bounds(self):
        for value in [0, 30, 100]:
            self.assertEqual(self.ia._sane_valido(value),value)
        for value in [None, -1, 101, float('inf'), float('nan'), 'invalid']:
            self.assertEqual(self.ia._sane_valido(value,40),40)

    def test_lsi_nonfinite_and_flexion_missing(self):
        for value in [None, float('nan'), float('inf'), -1]:
            with self.subTest(value=value):
                self.assertIsNone(self.panel._calcular_lsi_seguro(value,40,'Direito')[0])
                self.assertIsNone(self.ia.calcular_lsi(value,40)['valor'])
        for value in [None, float('nan'), float('inf')]:
            result=self.ia.calcular_lsi(40,50,flex_lesado=24,flex_saudavel=value)
            self.assertIsNone(result['lsi_isquios'])
            self.assertEqual(result['razao_iq_lesado'],60)

    def test_all_visap_options_preserve_declared_points(self):
        baseline=questionnaire('VISA-P Completo',{})
        for key,options in [('vp7',baseline['op_vp7']),('vp8',baseline['op_vp8'])]:
            for option in options:
                with self.subTest(key=key, option=option):
                    expected=int(option.rsplit('(',1)[1].split()[0])
                    result=questionnaire('VISA-P Completo',{**{f'vp{i}':0 for i in range(1,7)},key:option})
                    self.assertEqual(result['score_visap_calc'],expected)

    def test_all_ikdc_options_preserve_declared_points(self):
        baseline=questionnaire('IKDC Subjetivo',{})
        for key,options in [('ik2',baseline['op_ik_freq']),('ik_at',baseline['op_ik_at'])]:
            for option in options:
                with self.subTest(key=key,option=option):
                    points=int(option.rsplit('(',1)[1].split()[0])
                    responses=dict(ik1=0,ik2='Constante (0 pts)',ik_at='Incapaz (0 pts)',ik4=0)
                    responses[key]=option
                    self.assertAlmostEqual(questionnaire('IKDC Subjetivo',responses)['score_ikdc_calc'],points*2)

    def test_bilateral_iq_keeps_flexion_and_extension_on_same_limb(self):
        class Adapter:
            def read(self,collection):
                return pd.DataFrame([{'Nome':'Ficticio C','Diagnostico_Clinico':''}])
            def read_paciente(self,collection,name):
                assert name=='Ficticio C'
                if collection=='Evolucao': return pd.DataFrame()
                return pd.DataFrame([dict(Lado_Acometido='Bilateral',Dinamometria_Dir='Ext:20 Flex:30',Dinamometria_Esq='Ext:40 Flex:10')])
        self.ia.analisar_paciente.__globals__['conn']=Adapter()
        result=self.ia.analisar_paciente('Ficticio C')['lsi']
        self.assertEqual(result['razao_iq_lesado'],150)
        self.assertEqual(result['razao_iq_saudavel'],25)

    def test_prognosis_endpoints_and_missing_fallback(self):
        df=pd.DataFrame({'Data_dt':pd.to_datetime(['2026-01-01','2026-04-23']),'Sessão_Num':[1,2],'SANE_Pct_Num':[30,float('nan')]})
        before=df.copy(deep=True)
        r=self.panel._calcular_curva_prognostica_sane(df,df,30,16)
        self.assertEqual(r['esperado'],[30,85])
        self.assertEqual(r['real'],[30,30])
        pd.testing.assert_frame_equal(df,before)

    def test_patient_isolation_with_fake_adapter_and_unsorted_dates(self):
        # No Firebase adapter is imported: all reads resolve to this in-memory double.
        evolutions={name:pd.DataFrame([{'Paciente':name,'Data':'2026-01-02','Dor':2,'SANE_Pct':sane},{'Paciente':name,'Data':'2026-01-01','Dor':8,'SANE_Pct':10}]) for name,sane in [('Ficticio A',80),('Ficticio B',20)]}
        evaluations={name:pd.DataFrame([dict(Paciente=name,Data_Avaliacao='01/01/2026',SANE_Baseline_Pct=10,Lado_Acometido='Direito',Dinamometria_Dir=f'Ext:{force} Flex:12',Dinamometria_Esq='Ext:40 Flex:24')]) for name,force in [('Ficticio A',36),('Ficticio B',20)]}
        original=copy.deepcopy(evolutions)
        calls=[]
        class Adapter:
            def read(self, collection):
                assert collection=='Cadastro'
                return pd.DataFrame([{'Nome':name,'Diagnostico_Clinico':''} for name in evolutions])
            def read_paciente(self,collection,name):
                calls.append((collection,name))
                return (evolutions if collection=='Evolucao' else evaluations)[name].copy(deep=True)
        self.ia.analisar_paciente.__globals__['conn']=Adapter()
        a=self.ia.analisar_paciente('Ficticio A')
        b=self.ia.analisar_paciente('Ficticio B')
        again=self.ia.analisar_paciente('Ficticio A')
        self.assertEqual((a['lsi']['valor'],b['lsi']['valor']),(90,50))
        self.assertEqual((a['percepcao_metas']['sane_atual'],b['percepcao_metas']['sane_atual']),(80,20))
        self.assertEqual(a['percepcao_metas'],again['percepcao_metas'])
        self.assertEqual(a['sessoes_registradas'],2)
        self.assertEqual(len(calls),6)
        for name in evolutions: pd.testing.assert_frame_equal(evolutions[name],original[name])


if __name__=='__main__':
    unittest.main()
