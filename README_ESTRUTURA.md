# GENUA | Estrutura Modular

## Arquitetura

```
meu-app-fisio/
├── streamlit_app.py          ← entrypoint (orquestra tudo)
├── config.py                 ← cores, logo, CSS, set_page_config, helper titulo()
├── firebase_client.py        ← init Firebase + FirebaseAdapter
├── routing.py                ← portal do cirurgião + session_state inicial
├── ui_login.py               ← Tela 1: Login
├── ui_dados_paciente.py      ← Tela 2: Cadastro/Seleção
├── modulo_avaliacao.py       ← Tela 3 - Módulo 1: Avaliação Inicial 🔎
├── modulo_checkin.py         ← Tela 3 - Módulo 2: Check-in Diário 📝
└── modulo_painel.py          ← Tela 3 - Módulo 3: Painel Analítico 📊
```

## Como subir no GitHub

1. Substitua o `streamlit_app.py` antigo pelo novo
2. Adicione os outros 8 arquivos **na raiz** (mesma pasta do `streamlit_app.py`)
3. `requirements.txt` permanece igual — nenhuma dependência nova

## Fluxo de execução

```
streamlit_app.py (entrypoint)
  └─> import config        (aplica CSS, page_config, logo na sidebar)
  └─> aplicar_roteamento() (lê URL: portal do cirurgião?)
  └─> despacha pra tela:
        ├─ login          → ui_login.render()
        ├─ dados_paciente → ui_dados_paciente.render()
        └─ painel_clinico → sidebar com menu, depois:
                            ├─ modulo_avaliacao.render()
                            ├─ modulo_checkin.render()
                            └─ modulo_painel.render()
```

## Onde editar o quê

| Quero mexer em… | Vou em… |
|---|---|
| Cores, fontes, CSS, logo | `config.py` |
| Coleções Firebase ou query | `firebase_client.py` |
| Lógica de portal do cirurgião | `routing.py` |
| Tela de login | `ui_login.py` |
| Cadastro de paciente | `ui_dados_paciente.py` |
| Anamnese, exame físico, PROMs (LEFS/KOOS/etc) | `modulo_avaliacao.py` |
| Check-in diário (EVA, ADM, sono) | `modulo_checkin.py` |
| Dashboard, cérebro clínico, PDF | `modulo_painel.py` |

## Workflow com Gemini agora

Antes: jogava o arquivo de 1685 linhas pro Gemini, ele bagunçava tudo.
Agora: cola **só o módulo relevante** (50-550 linhas) e pede o ajuste — o resto fica blindado.

Exemplo:
- "Adiciona um campo X na avaliação inicial" → cola só `modulo_avaliacao.py`
- "Muda a cor do botão de login" → cola só `config.py` + `ui_login.py`
