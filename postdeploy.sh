#!/usr/bin/env bash

echo "--- Executando scripts pós-deploy ---"
python manage.py migrate
python manage.py create_superuser_if_none --username admin --email admin@example.com --password admin123