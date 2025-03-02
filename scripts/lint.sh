#!/bin/bash
  
set -e

pipenv run ruff format
pipenv run mypy --install-types --check-untyped-defs --no-namespace-packages .