#!/bin/bash
echo "🚀 Setting up local environment..."

# 1. Create venv if not exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "📦 Virtual environment created."
fi

# 2. Activate and install deps
source venv/bin/activate
pip install -r requirements.txt

# 2.5 Load .env variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# OVERRIDE for Local Dev (No Docker)
export POSTGRES_USER=""  # Force SQLite fallback
export API_HOST="http://localhost:8000"

# 3. Start API in background
echo "🟢 Starting Core API..."
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# 4. Wait for API to be ready (dumb sleep)
sleep 3

# 5. Start Bot
echo "🤖 Starting Telegram Bot..."
# Ensure env vars are loaded for bot (simplest way is export or python-dotenv logic inside app)
# We assume .env is read by the python app using pydantic settings or dotenv
python -m app.bot.main

# Cleanup on exit
kill $API_PID
