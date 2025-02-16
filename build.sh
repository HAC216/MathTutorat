#!/bin/bash

# Installer les dépendances
pip install -r requirements.txt


# Collecter les fichiers statiques
python manage.py collectstatic --noinput
