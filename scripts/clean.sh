#!/bin/bash

rm -r venv
find . -name '*.pyc' -delete
find . -name '__pycache__' -delete
find . -name '*.egg-info' -exec rm -rv {} \;

echo Cleaned project!
