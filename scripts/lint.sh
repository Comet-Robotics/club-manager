#!/bin/bash
  
set -e
pipenv run ruff format

# Allowing mypy to fail for now - need to gradually work on ensuring types are handled correctly in the codebase
set +e 
pipenv run mypy --install-types --check-untyped-defs --no-namespace-packages .