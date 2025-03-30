#!/usr/bin/env bash
set -e  # Encerra o script imediatamente se qualquer comando falhar

echo "➤ Atualizando pip e dependências..."
pip install --upgrade pip
pip install -r requirements.txt

echo "➤ Verificando configuração do banco de dados..."
if [ "$RENDER_SERVICE_TYPE" = "web" ]; then
  echo "✓ Configurando para ambiente Render.com"
  
  # Apenas executa migrações se for PostgreSQL (SQLite não persiste)
  if [ -z "$DATABASE_URL" ] || [[ "$DATABASE_URL" == *"sqlite"* ]]; then
    echo "⚠ ATENÇÃO: SQLite detectado - dados serão perdidos entre deploys!"
    echo "Recomendado: Migre para PostgreSQL no Render Dashboard"
  fi
  
  echo "➤ Aplicando migrações..."
  python manage.py migrate --no-input
  
  echo "➤ Criando superusuário se necessário..."
  python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model() 
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✓ Superusuário criado')
else:
    print('✓ Superusuário já existe')
"
fi

echo "➤ Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "✓ Build concluído com sucesso!"