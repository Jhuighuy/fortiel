#!/usr/bin/env bash

rm -rf dist
python3 setup.py sdist
twine check dist/* && twine upload dist/*
