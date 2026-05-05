#!/bin/bash

cd "$(dirname "$0")" || exit 1

echo "Starting Docker Desktop..."
open -a Docker

echo "Waiting for Docker to start..."
sleep 20

echo "Running docker compose (with build)..."
osascript -e 'tell application "Terminal" to do script "cd '"$(pwd)"' && docker compose up --build"'

echo "Waiting for Streamlit to be ready..."
sleep 20

echo "Opening browser..."
open http://localhost:8501