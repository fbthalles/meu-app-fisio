# Inventário literal dos instrumentos implementados

Base: `613f7428cfc5399f8c833f7969b53bb1b5964278`.
Extração de código, não reprodução de instrumentos oficiais nem validação científica.
Inclui itens, opções, pesos e fórmulas efetivamente executados.


## KOOS-12 /

`modulo_avaliacao.py:1270`

```python
            with st.expander("🟢 KOOS-12 / Domínios Completos (Lesões de Joelho, LCA, Menisco, Condropatia e OA)", expanded=("KOOS" in proms_aplicados)):
                koos_op = {"Extremo / Sempre (0)": 0, "Severo / Frequente (1)": 1, "Moderado (2)": 2, "Leve / Raro (3)": 3, "Nenhum / Nunca (4)": 4}
                lista_k_op = list(koos_op.keys())
                perguntas_koos12 = [
                    ("k1", "1. Sintomas: Inchaço / Efusão no joelho"),
                    ("k2", "2. Sintomas: Estalidos, rangidos ou travamento ao mover"),
                    ("k3", "3. Sintomas: Rigidez matinal ou após ficar sentado"),
                    ("k4", "4. Dor: Frequência com que sente dor no joelho"),
                    ("k5", "5. Dor: Ao girar/torcer sobre o joelho"),
                    ("k6", "6. Dor: Ao esticar totalmente ou dobrar totalmente o joelho"),
                    ("k7", "7. Dor: Ao subir ou descer escadas"),
                    ("k8", "8. Função (AVDs): Levantar-se de uma cadeira ou entrar/sair do carro"),
                    ("k9", "9. Função (AVDs): Ficar em pé ou caminhar em superfície plana"),
                    ("k10", "10. Esporte/Recreação: Agachar, correr ou saltar"),
                    ("k11", "11. Qualidade de Vida: Modificou seu estilo de vida para evitar sobrecarga no joelho?"),
                    ("k12", "12. Qualidade de Vida: Falta de confiança no joelho no dia a dia"),
                ]
                ck1, ck2 = st.columns(2)
                score_koos_bruto = 0
                for idx_k, (ch_k, label_k) in enumerate(perguntas_koos12):
                    with (ck1 if idx_k < 6 else ck2):
                        esc_k = st.selectbox(label_k, lista_k_op, index=_idx_prom(lista_k_op, ch_k, 4), key=ch_k)
                        novas_respostas_proms[ch_k] = esc_k
                        score_koos_bruto += koos_op[esc_k]

                pct_koos_calc = (score_koos_bruto / (len(perguntas_koos12) * 4)) * 100.0
                interp_koos_calc = "🚨 Risco Funcional" if pct_koos_calc < 40 else "🟡 Limitação Moderada" if pct_koos_calc < 80 else "🟢 Alta Performance"
                st.info(f"📊 **Resultado KOOS-12:** **{pct_koos_calc:.1f}%** — {interp_koos_calc} *(MCID: 8-10 pts | Roos 2003)*")
```


## IKDC Subjetivo

`modulo_avaliacao.py:1300`

```python
            with st.expander("✚ IKDC Subjetivo (Avaliação Ligamentar, Meniscal e Cartilaginosa)", expanded=("IKDC" in proms_aplicados)):
                c_ik1, c_ik2 = st.columns(2)
                op_ik_freq = ["Constante (0 pts)", "Diária (2 pts)", "Semanal (4 pts)", "Rara (7 pts)", "Nenhuma (10 pts)"]
                op_ik_at = ["Incapaz (0 pts)", "Atividades Leves (3 pts)", "Moderadas / Corrida leve (6 pts)", "Esporte Intenso / Corte e Giro (10 pts)"]
                with c_ik1:
                    ik_dor = st.slider("1. Nível de Alívio de Dor (0=Dor insuportável, 10=Sem dor)", 0, 10, _val_prom("ik1", 10), key="ik1")
                    ik_freq = st.selectbox("2. Frequência da Dor", op_ik_freq, index=_idx_prom(op_ik_freq, "ik2", 4), key="ik2")
                    ik_at_nivel = st.selectbox("3. Nível de atividade que consegue realizar sem dor/falseio", op_ik_at, index=_idx_prom(op_ik_at, "ik_at", 3), key="ik_at")
                with c_ik2:
                    ik_func = st.slider("4. Função do Joelho Antes da Lesão (0-10)", 0, 10, _val_prom("ik3", 10), key="ik3")
                    ik_func_atual = st.slider("5. Função Global do Joelho Hoje (0-10)", 0, 10, _val_prom("ik4", 5), key="ik4")

                ik_pts_freq = 0 if "(0 pts)" in ik_freq else 2 if "(2 pts)" in ik_freq else 4 if "(4 pts)" in ik_freq else 7 if "(7 pts)" in ik_freq else 10
                ik_pts_at = 0 if "(0 pts)" in ik_at_nivel else 3 if "(3 pts)" in ik_at_nivel else 6 if "(6 pts)" in ik_at_nivel else 10
                for k_ik, v_ik in [("ik1", ik_dor), ("ik2", ik_freq), ("ik_at", ik_at_nivel), ("ik3", ik_func), ("ik4", ik_func_atual)]:
                    novas_respostas_proms[k_ik] = v_ik

                score_ikdc_calc = min(100.0, ((ik_dor + ik_pts_freq + ik_pts_at + (ik_func_atual * 2)) / 50.0) * 100.0)
                interp_ikdc_calc = "🚨 Baixa Função Subjetiva" if score_ikdc_calc < 60 else "🟡 Desempenho Moderado" if score_ikdc_calc < 85 else "🟢 Excelente Desempenho"
                st.info(f"📊 **Resultado IKDC:** **{score_ikdc_calc:.1f}%** — {interp_ikdc_calc} *(MCID: 9 pts | Irrgang 2006)*")
```


## LEFS (

`modulo_avaliacao.py:1322`

```python
            with st.expander("📝 LEFS (Escala Funcional da Extremidade Inferior — 10 Atividades Chave)", expanded=("LEFS" in proms_aplicados)):
                opcoes_lefs = {
                    "Incapaz / Extrema Dificuldade": 0, "Muita Dificuldade": 1,
                    "Dificuldade Moderada": 2, "Um Pouco de Dificuldade": 3, "Nenhuma Dificuldade": 4
                }
                lista_k_lefs = list(opcoes_lefs.keys())
                perguntas_lefs = [
                    "1. Trabalho, tarefas domésticas ou escola",
                    "2. Agachar ou ajoelhar",
                    "3. Andar 2 quarteirões",
                    "4. Subir um lance de escadas",
                    "5. Descer um lance de escadas",
                    "6. Ficar em pé por 1 hora",
                    "7. Correr em terreno plano",
                    "8. Correr em terreno irregular",
                    "9. Saltar / Pular",
                    "10. Mudança rápida de direção (Corte)",
                ]
                score_lefs = 0
                c_l1, c_l2 = st.columns(2)
                for i, p in enumerate(perguntas_lefs):
                    with (c_l1 if i < 5 else c_l2):
                        esc_l = st.selectbox(p, lista_k_lefs, index=_idx_prom(lista_k_lefs, f"lefs_{i}", 0), key=f"lefs_{i}")
                        novas_respostas_proms[f"lefs_{i}"] = esc_l
                        score_lefs += opcoes_lefs[esc_l]

                pct_lefs_calc = (score_lefs / (len(perguntas_lefs) * 4)) * 100.0
                pts_lefs_80_calc = round((pct_lefs_calc / 100.0) * 80, 1)
                interp_lefs_calc = (
                    "🚨 Função Muito Ruim" if pct_lefs_calc < 30 else
                    "🟡 Função Regular" if pct_lefs_calc < 60 else
                    "🟢 Função Boa" if pct_lefs_calc < 85 else
                    "⭐ Função Excelente"
                )
                st.info(f"📊 **Resultado LEFS:** {pts_lefs_80_calc}/80 pts equivalentes (**{pct_lefs_calc:.1f}%**) — {interp_lefs_calc} *(MCID: 9 pts | Binkley 1999)*")
```


## VISA-P Completo

`modulo_avaliacao.py:1359`

```python
            with st.expander("🎯 VISA-P Completo (Tendinopatia Patelar — 8 itens oficiais)", expanded=("VISA-P" in proms_aplicados)):
                c_v1, c_v2 = st.columns(2)
                with c_v1:
                    vp1 = st.slider("1. Minutos sentado sem dor (0-10)", 0, 10, _val_prom("vp1", 10), key="vp1")
                    vp2 = st.slider("2. Dor ao descer escadas em ritmo normal", 0, 10, _val_prom("vp2", 10), key="vp2")
                    vp3 = st.slider("3. Dor ao estender ativamente o joelho sem peso", 0, 10, _val_prom("vp3", 10), key="vp3")
                    vp4 = st.slider("4. Dor ao fazer afundo (lunge) com descarga de peso", 0, 10, _val_prom("vp4", 10), key="vp4")
                with c_v2:
                    vp5 = st.slider("5. Problemas para agachar totalmente", 0, 10, _val_prom("vp5", 10), key="vp5")
                    vp6 = st.slider("6. Dor durante/após 10 saltos unipodais", 0, 10, _val_prom("vp6", 10), key="vp6")
                    op_vp7 = ["Não consegue (0 pts)", "Treino modificado (4 pts)", "Treino completo mas nível reduzido (7 pts)", "Competindo no mesmo nível ou maior (10 pts)"]
                    p7 = st.selectbox("7. Prática Esportiva Atual", op_vp7, index=_idx_prom(op_vp7, "vp7", 0), key="vp7")
                    op_vp8 = ["Dor impede o treino (0 pts)", "Treina até 15 min antes de parar (7 pts)", "Treina com dor suportável (15 pts)", "Treina sem nenhuma dor (30 pts)"]
                    p8 = st.selectbox("8. Tempo de tolerância ao treino/esporte", op_vp8, index=_idx_prom(op_vp8, "vp8", 0), key="vp8")

                for k_vp, v_vp in [("vp1", vp1), ("vp2", vp2), ("vp3", vp3), ("vp4", vp4), ("vp5", vp5), ("vp6", vp6), ("vp7", p7), ("vp8", p8)]:
                    novas_respostas_proms[k_vp] = v_vp

                score_visap_calc = vp1 + vp2 + vp3 + vp4 + vp5 + vp6
                score_visap_calc += 0 if "(0 pts)" in p7 else 4 if "(4 pts)" in p7 else 7 if "(7 pts)" in p7 else 10
                score_visap_calc += 0 if "(0 pts)" in p8 else 7 if "(7 pts)" in p8 else 15 if "(15 pts)" in p8 else 30
                interp_visap_calc = "🚨 Tendinopatia Severa/Aguda" if score_visap_calc < 50 else "🟡 Fase Reativa" if score_visap_calc < 80 else "🟢 Remodelamento/Alta"
                st.info(f"📊 **Resultado VISA-P:** **{score_visap_calc}/100 pontos** — {interp_visap_calc} *(MCID: 13 pts | Hernandez-Sanchez 2014)*")
```


## Lysholm Completa

`modulo_avaliacao.py:1384`

```python
            with st.expander("🦵 Escala de Lysholm Completa (8 domínios oficiais — 100 pts)", expanded=("Lysholm" in proms_aplicados)):
                c_ly1, c_ly2 = st.columns(2)
                op_ly_mancar = ["5 - Nenhum", "3 - Leve ou Periódico", "0 - Grave ou Constante"]
                op_ly_apoio = ["5 - Nenhum (Marcha livre)", "2 - Usa bengala ou muleta", "0 - Descarga de peso impossível"]
                op_ly_trav = ["15 - Nenhum travamento ou bloqueio", "10 - Sensação de fisgada sem bloqueio", "6 - Bloqueio ocasional", "2 - Bloqueio frequente", "0 - Articulação bloqueada no exame"]
                op_ly_inst = ["25 - Nunca falseia", "20 - Raramente no esporte intenso", "15 - Frequentemente no esporte intenso", "10 - Ocasionalmente nas AVDs", "5 - Frequentemente nas AVDs", "0 - A cada passo"]
                op_ly_dor = ["25 - Nenhuma", "20 - Inconstante e leve no exercício intenso", "15 - Marcada no exercício intenso", "10 - Marcada após caminhar > 2 km", "5 - Marcada após caminhar < 2 km", "0 - Constante"]
                op_ly_inc = ["10 - Nenhum", "6 - No exercício intenso", "2 - Nos esforços comuns / AVDs", "0 - Constante"]
                op_ly_esc = ["10 - Sem problemas", "6 - Levemente prejudicado", "2 - Um degrau de cada vez", "0 - Impossível"]
                op_ly_aga = ["5 - Sem problemas", "4 - Levemente prejudicado", "2 - Não passa de 90°", "0 - Impossível"]

                with c_ly1:
                    ly1 = st.selectbox("1. Claudicação (Mancar)", op_ly_mancar, index=_idx_prom(op_ly_mancar, "ly1", 0), key="ly1")
                    ly2 = st.selectbox("2. Apoio (Muletas/Bengala)", op_ly_apoio, index=_idx_prom(op_ly_apoio, "ly2", 0), key="ly2")
                    ly3 = st.selectbox("3. Bloqueio / Travamento", op_ly_trav, index=_idx_prom(op_ly_trav, "ly3", 0), key="ly3")
                    ly4 = st.selectbox("4. Instabilidade (Falseio)", op_ly_inst, index=_idx_prom(op_ly_inst, "ly4", 0), key="ly4")
                with c_ly2:
                    ly5 = st.selectbox("5. Dor", op_ly_dor, index=_idx_prom(op_ly_dor, "ly5", 0), key="ly5")
                    ly6 = st.selectbox("6. Edema / Inchaço", op_ly_inc, index=_idx_prom(op_ly_inc, "ly6", 0), key="ly6")
                    ly7 = st.selectbox("7. Subir Escadas", op_ly_esc, index=_idx_prom(op_ly_esc, "ly7", 0), key="ly7")
                    ly8 = st.selectbox("8. Agachamento", op_ly_aga, index=_idx_prom(op_ly_aga, "ly8", 0), key="ly8")

                lista_ly = [("ly1", ly1), ("ly2", ly2), ("ly3", ly3), ("ly4", ly4), ("ly5", ly5), ("ly6", ly6), ("ly7", ly7), ("ly8", ly8)]
                score_lysholm_calc = 0
                for k_ly, v_ly in lista_ly:
                    novas_respostas_proms[k_ly] = v_ly
                    score_lysholm_calc += int(v_ly.split(" -")[0])

                interp_lysholm_calc = "🚨 Ruim (<65)" if score_lysholm_calc < 65 else "🟡 Regular (65-83)" if score_lysholm_calc < 84 else "🟢 Bom (84-94)" if score_lysholm_calc < 95 else "⭐ Excelente (95-100)"
                st.info(f"📊 **Resultado Lysholm:** **{score_lysholm_calc}/100 pontos** — {interp_lysholm_calc} *(MCID: 10 pts | Briggs 2009)*")
```


## Índice WOMAC

`modulo_avaliacao.py:1416`

```python
            with st.expander("🦴 Índice WOMAC (Osteoartrite — Dor, Rigidez e Função)", expanded=("WOMAC" in proms_aplicados)):
                w_op = {"Nenhuma": 0, "Leve": 1, "Moderada": 2, "Intensa": 3, "Muito Intensa": 4}
                lista_w_keys = list(w_op.keys())
                score_womac_bruto = 0
                c_w1, c_w2, c_w3 = st.columns(3)
                with c_w1:
                    st.markdown("**Dor (5 itens)**")
                    for p in ["Andar no plano", "Subir/descer escadas", "À noite na cama", "Sentar ou deitar", "Ficar em pé"]:
                        esc_w = st.selectbox(p, lista_w_keys, index=_idx_prom(lista_w_keys, f"wd_{p}", 0), key=f"wd_{p}")
                        novas_respostas_proms[f"wd_{p}"] = esc_w
                        score_womac_bruto += w_op[esc_w]
                with c_w2:
                    st.markdown("**Rigidez (2 itens)**")
                    for p in ["Rigidez matinal", "Rigidez ao final do dia"]:
                        esc_w = st.selectbox(p, lista_w_keys, index=_idx_prom(lista_w_keys, f"wr_{p}", 0), key=f"wr_{p}")
                        novas_respostas_proms[f"wr_{p}"] = esc_w
                        score_womac_bruto += w_op[esc_w]
                with c_w3:
                    st.markdown("**Função - AVDs (8 itens)**")
                    for p in ["Descer escadas", "Levantar da cadeira", "Ficar em pé", "Entrar/Sair do carro", "Calçar meias", "Sair da cama", "Entrar/sair do banho", "Tarefas domésticas"]:
                        esc_w = st.selectbox(p, lista_w_keys, index=_idx_prom(lista_w_keys, f"wf_{p}", 0), key=f"wf_{p}")
                        novas_respostas_proms[f"wf_{p}"] = esc_w
                        score_womac_bruto += w_op[esc_w]

                max_w = (5 + 2 + 8) * 4
                pct_womac_calc = 100.0 - ((score_womac_bruto / max_w) * 100.0)
                interp_womac_calc = "🚨 Limitação Severa" if pct_womac_calc < 30 else "🟡 Limitação Moderada" if pct_womac_calc < 70 else "🟢 Limitação Leve" if pct_womac_calc < 90 else "⭐ Excelente"
                st.info(f"📊 **Resultado WOMAC:** **{pct_womac_calc:.1f}%** — {interp_womac_calc}")
```
