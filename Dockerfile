# Use uma imagem Python mais leve como base
FROM python:3.12-slim-bullseye AS base

# Defina variáveis de ambiente
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Defina o diretório de trabalho
WORKDIR /app

# Instale dependências do sistema necessárias para mysqlclient e remova arquivos desnecessários
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \ 
    default-libmysqlclient-dev \  
    libncurses5-dev \
    libncursesw5-dev \
    locales \
    && locale-gen pt_BR.UTF-8 \
    && dpkg-reconfigure locales \
    && rm -rf /var/lib/apt/lists/*

# Configurações de locale
ENV LANG pt_BR.UTF-8
ENV LANGUAGE pt_BR:pt
ENV LC_ALL pt_BR.UTF-8

# Copie o arquivo de requisitos e instale as dependências
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação
COPY . /app/

EXPOSE 8001

# Comando para iniciar o servidor
CMD ["daphne", "-b", "0.0.0.0", "-p", "8001", "menudog.asgi:application"]
