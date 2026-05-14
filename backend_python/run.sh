#!/bin/bash

# Python Voice Task Manager Backend Setup

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Starting Python backend..."
uvicorn main:app --reload --host 0.0.0.0 --port 8888
