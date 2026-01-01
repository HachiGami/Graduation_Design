#!/bin/bash
echo "Starting Backend Server..."
cd "$(dirname "$0")"
uvicorn app.main:app --reload --port 8000






