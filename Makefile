# bash needed for pipefail
SHELL := /bin/bash

test: test_unit

test_unit:
	mkdir -p build
	coverage run -m pytest tests/unit
	coverage xml
	coverage report
