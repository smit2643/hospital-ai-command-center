PYTHON ?= python3

.PHONY: setup migrate superuser seed run worker test docker-up docker-down

setup:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

migrate:
	$(PYTHON) manage.py migrate

superuser:
	$(PYTHON) manage.py createsuperuser

seed:
	$(PYTHON) manage.py seed_demo

run:
	$(PYTHON) manage.py runserver

worker:
	celery -A hospital_ai worker -l info

test:
	$(PYTHON) manage.py test

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
