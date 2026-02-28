# 1. Imagem base oficial do Python
FROM python:3.11-slim

# 2. Configurações de sistema
WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# 3. Copia os ficheiros do GitHub para dentro do servidor
COPY . .

# 4. Instala as dependências científicas e o motor Firebase
RUN pip install --no-cache-dir -r requirements.txt

# 5. Expõe a porta padrão da Google Cloud
EXPOSE 8080

# 6. Comando para ligar o GENUA
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8080", "--server.address=0.0.0.0"]
