#!/bin/bash
  
set -e

ruff check
pylint .
mypy --install-types --check-untyped-defs .