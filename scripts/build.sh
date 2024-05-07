#!/bin/bash

cd backend
export PYTHONPATH=..
python manage.py build --port=$1
