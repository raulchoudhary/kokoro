#!/bin/bash
echo "Installing requirements..."
pip install -r requirements.txt
echo "Installing uvicorn directly..."
pip install uvicorn
echo "Checking uvicorn installation..."
pip show uvicorn
echo "Starting application..."
python -m uvicorn main:app --host 0.0.0.0 --port $PORT
