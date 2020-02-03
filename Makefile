# bash needed for pipefail
SHELL := /bin/bash

test: test_unit

test_unit:
	nosetests --with-coverage tests/unit
