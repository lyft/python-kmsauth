# bash needed for pipefail
SHELL := /bin/bash

test: test_unit

test_unit:
	mkdir -p build
	nosetests --with-coverage tests/unit
