#!/bin/bash
 
set -e # Cause script to exit if any command fails

pipenv run ruff format --check

pipenv run mypy . --install-types --check-untyped-defs --no-namespace-packages
