#!/bin/bash
 
set -e # Cause script to exit if any command fails

pipenv run ruff format --check

# But, we're allowing mypy to fail for now and still consider linting to be 'successful' - we need to gradually work on ensuring types are handled correctly in the codebase
set +e 

pipenv run mypy --install-types --check-untyped-defs --no-namespace-packages .

exit 0
