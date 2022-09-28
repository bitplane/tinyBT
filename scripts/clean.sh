#!/bin/bash

rm -r venv
find . -name '*.pyc' -delete
find . -name '__pycache__' -delete
find . -name '.coverage' -delete
find . -name '*.egg-info' -exec rm -rv {} \;
rm -r htmlcov

echo Cleaned project!
