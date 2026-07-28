# 🦵 GENUA | Inteligência Clínica

> Plataforma de gestão fisioterapêutica com foco em joelho, baseada em ciência real, para uso da equipe clínica da **Genua Instituto de Fisioterapia Esportiva** (São Paulo).

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Firebase](https://img.shields.io/badge/Firebase-FFA000?style=for-the-badge&logo=firebase&logoColor=white)](https://firebase.google.com)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

---

## 📋 O que o app faz

O GENUA é um sistema completo de acompanhamento fisioterapêutico com **3 módulos clínicos integrados**, alimentando um cérebro clínico baseado em evidência científica:

- **🔎 Avaliação Inicial** — anamnese, bandeiras, exame físico, dinamometria, controle motor e PROMs (LEFS, VISA-P, Lysholm, WOMAC, KOOS, IKDC)
- **📝 Check-in Diário** — EVA, inchaço, ADM, sono e testes funcionais dinâmicos
- **📊 Painel Analítico** — dashboard, árvore de decisão por fenótipo, gráficos e laudo PDF

---

## 🏗️ Arquitetura

O app está organizado em **9 módulos** com responsabilidade única, facilitando manutenção e evolução:

```
meu-app-fisio/
├── streamlit_app.py          ← Entrypoint — orquestra tudo
├── config.py                 ← Cores, logo, CSS responsivo, helpers (titulo/toast/secao)
├── firebase_client.py        ← Conexão Firestore + cache TTL 60s
├── routing.py                ← Portal do cirurgião (deep-link)
├── ui_login.py               ← Tela de Login
├── ui_dados_paciente.py      ← Cadastro/seleção de paciente
├── modulo_avaliacao.py       ← 🔎 Avaliação Inicial
├── modulo_checkin.py         ← 📝 Check-in Diário
├── modulo_painel.py          ← 📊 Painel Analítico + PDF
├── requirements.txt          ← Dependências Python
├── logo_genua_novo_v2.png    ← Logo institucional
└── mapa_joelho.png           ← Mapa anatômico interativo
```

### Onde editar o quê

| Quero mexer em… | Vou em… |
|---|---|
| Cores, fontes, CSS, logo | `config.py` |
| Coleções Firebase ou queries | `firebase_client.py` |
| Portal do cirurgião | `routing.py` |
| Tela de login | `ui_login.py` |
| Cadastro de paciente | `ui_dados_paciente.py` |
| Anamnese, exame físico, PROMs | `modulo_avaliacao.py` |
| Check-in diário (EVA, ADM, sono) | `modulo_checkin.py` |
| Dashboard, cérebro clínico, PDF | `modulo_painel.py` |

---

## 🧠 Coleções Firestore

| Coleção | Conteúdo | Quando é escrita |
|---|---|---|
| `Cadastro` | Dados pessoais do paciente | Ao cadastrar novo paciente |
| `Avaliacao_Inicial` | Anamnese + exame físico + PROMs | Ao salvar avaliação |
| `Evolucao` | Check-ins diários (EVA, ADM, sono) | Ao salvar check-in |

⚠️ **Não alterar os nomes das coleções** — quebra a leitura dos históricos existentes.

---

## 🚀 Como rodar localmente

```bash
# 1. Clone o repo
git clone https://github.com/fbthalles/meu-app-fisio.git
cd meu-app-fisio

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure secrets (credenciais Firebase)
mkdir .streamlit
echo 'FIREBASE_JSON = """<seu-json-aqui>"""' > .streamlit/secrets.toml

# 4. Rode o app
streamlit run streamlit_app.py
```

---

## ☁️ Deploy

O app é hospedado no **Streamlit Cloud** com auto-deploy:

1. Push no branch `main` do GitHub
2. Streamlit Cloud detecta e faz redeploy em ~30s
3. Ambiente sem Docker, sem containerização — Streamlit gerencia tudo

**Secrets do Firebase** são configurados no painel web do Streamlit Cloud (Settings → Secrets), não no repo.

---

## 🎯 Roadmap

### ✅ Fase 1 — Fundação UX/UI (concluída)
- Modularização em 9 arquivos
- Cache Firebase com TTL 60s + invalidação inteligente
- CSS responsivo (mobile / tablet / desktop)
- Lazy load de bibliotecas pesadas (matplotlib, FPDF, PIL)
- Helpers padronizados: `titulo()`, `toast()`, `secao()`

### 🔄 Fase 2 — IA Clínica Baseada em Evidência (em desenvolvimento)
- **Detector de estagnação** via MCID (Minimal Clinically Important Difference)
- **Painel de bandeiras** dinâmico (vermelha, amarela, azul, negra)
- **LSI automático** com thresholds da literatura (Grindem 2016)
- **Prognóstico por fenótipo** — trajetória paciente × trajetória esperada da literatura

### ⏳ Fase 3 — Laudo Clínico Premium (planejada)
- Migração de FPDF para ReportLab
- Radar chart das subescalas KOOS
- Comparação visual lado lesado × lado saudável
- Trajetória paciente sobreposta à literatura
- QR Code para agendamento de retorno

---

## 📚 Referências Científicas

Toda regra clínica do app é fundamentada em literatura peer-reviewed:

| PROM | MCID | Referência |
|---|---|---|
| EVA/VAS (dor) | ~2 pontos | Salaffi 2004 |
| LEFS | 9 pontos | Binkley 1999 |
| KOOS (por subescala) | 8-10 pontos | Roos 2003 |
| VISA-P | 13 pontos | Hernandez-Sanchez 2014 |
| LSI (Alta pós-LCA) | ≥ 90% | Grindem 2016 |

**Princípio inegociável:** IA aqui é *regra clínica explícita e auditável*, nunca LLM gerando parecer.

---

## 🔒 Privacidade & LGPD

- Processamento anonimizado de dados clínicos
- Finalidade exclusiva de inteligência clínica
- Portal do cirurgião com token criptografado (base64) para acesso pontual
- Sem compartilhamento com terceiros

---

## 🩺 Sobre a Genua

**Genua Instituto de Fisioterapia Esportiva** — Perdizes, São Paulo
Fisioterapia esportiva e ortopédica particular, 11 anos de operação, foco em joelho.

---

**Desenvolvido por Edgar Nunes** — Fisioterapeuta, empresário e diretor clínico
