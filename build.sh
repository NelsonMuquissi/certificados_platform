#!/bin/bash

echo "Atualizando o pip..."
pip install --upgrade pip

echo "Instalando dependências..."
pip install -r requirements.txt

echo "Instalando python-dotenv (caso não esteja no requirements.txt)..."
pip install python-dotenv
set -o errexit

echo "Verificando e instalando gunicorn..."
pip show gunicorn || pip install gunicorn


echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "Criando superusuário (se necessário)..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell

echo "Build concluído com sucesso!"

#!/usr/bin/env bash
# build.sh

