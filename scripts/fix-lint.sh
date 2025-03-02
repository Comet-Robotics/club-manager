#!/bin/bash
  
set -e

pipenv run ruff format
pipenv run ruff check --fix --unsafe-fixes