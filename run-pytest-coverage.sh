#!/bin/sh
poetry run pytest --cov=. --cov-report=html --cov-report=xml --cov-report=term  $1 $2 $3 $4 $5
