#!/bin/bash

source venv/bin/activate

coverage run "$(which pytest)" tests
coverage report
coverage html

[ -v "$DISPLAY" ] || open ./htmlcov/index.html &
