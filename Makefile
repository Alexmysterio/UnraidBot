SHELL := /bin/bash

.PHONY: help setup up down logs build test lint doctor

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Crea .env de forma interactiva
	bash scripts/setup.sh

up: ## Construye y arranca el contenedor
	docker compose up -d --build

down: ## Detiene el contenedor
	docker compose down

logs: ## Sigue los logs del bot
	docker compose logs -f --tail=200 unraidbot

build: ## Construye la imagen
	docker compose build

test: ## Ejecuta los tests
	python -m pytest -q

lint: ## Ejecuta el linter
	ruff check .

doctor: ## Diagnóstico de API y permisos dentro del contenedor
	docker compose exec unraidbot python -m bot.doctor
