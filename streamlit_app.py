import pandas as pd
from datetime import datetime, timedelta
import random

def gerar_dados_teste():
    pacientes = [
        {"nome": "Lucas Oliveira", "perfil": "sucesso"},
        {"nome": "Mariana Costa", "perfil": "postural"},
        {"nome": "Roberto Santos", "perfil": "sono_dependente"},
        {"nome": "Beatriz Ferreira", "perfil": "deficit_motor"},
        {"nome": "Ricardo Biondi", "perfil": "sensibilizado"}
    ]
    
    opcoes_sono = ["Ruim", "Regular", "Bom"]
    opcoes_postura = ["Sentado", "Equilibrado", "Em pé"]
    opcoes_func = ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"]
    
    dados = []
    data_inicial = datetime(2025, 11, 24) # Começando há 10 semanas

    for p in pacientes:
        for i in range(30): # 3x por semana por 10 semanas
            data_sessao = data_inicial + timedelta(days=(i // 3) * 7 + (i % 3) * 2)
            
            # Lógica clínica simplificada para o perfil
            if p['perfil'] == "sucesso":
                dor = max(0, 8 - (i // 3))
                func = opcoes_func[0] if i > 20 else opcoes_func[1] if i > 10 else opcoes_func[3]
                sono = "Bom" if i > 10 else "Regular"
                postura = "Em pé"
            elif p['perfil'] == "postural":
                postura = "Sentado" if random.random() > 0.5 else "Equilibrado"
                dor = random.randint(5, 8) if postura == "Sentado" else random.randint(2, 4)
                func = "Dor Moderada"
                sono = "Regular"
            elif p['perfil'] == "sono_dependente":
                sono = random.choice(opcoes_sono)
                dor = random.randint(7, 10) if sono == "Ruim" else random.randint(2, 4)
                func = "Dor Leve"
                postura = "Equilibrado"
            else: # sensibilizado ou déficit
                dor = random.randint(6, 9)
                sono = "Ruim"
                func = "Incapaz"
                postura = "Sentado"

            dados.append({
                "Data": data_sessao.strftime("%d/%m/%Y %H:%M"),
                "Paciente": p['nome'],
                "Dor": dor,
                "Sono": sono,
                "Postura": postura,
                "Agachamento": func,
                "Step_Up": func,
                "Step_Down": func
            })
            
    return pd.DataFrame(dados)

df_teste = gerar_dados_teste()
df_teste.to_csv("dados_teste_genua.csv", index=False)
print("Arquivo 'dados_teste_genua.csv' gerado com 150 linhas!")
