#!/usr/bin/env bash
set -e

cp -n .env.example .env || true
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
