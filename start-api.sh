#!/bin/bash
# Start only the FastAPI backend
cd backend
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
