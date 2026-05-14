#!/bin/bash
# PEA - Personal Experience Amplifier
# One-click startup script

set -e

echo "==================================="
echo " PEA - Personal Experience Amplifier"
echo "==================================="
echo ""

# Check .env
if [ ! -f .env ]; then
    echo "[!] No .env file found."
    echo "    Copying .env.example to .env..."
    cp .env.example .env
    echo "    [!] Please edit .env and set your LLM API key before continuing."
    echo "    Required: DEEPSEEK_API_KEY (or QWEN_API_KEY / GLM_API_KEY / MOONSHOT_API_KEY)"
    exit 1
fi

echo "[1/4] Initializing database..."
cd backend
python init_db.py
cd ..

echo "[2/4] Starting ChromaDB..."
docker run -d --name pea-chromadb -p 8100:8000 -v chroma_data:/chroma/chroma chromadb/chroma:latest 2>/dev/null || echo "  ChromaDB container already running"

echo "[3/4] Starting backend..."
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

echo "[4/4] Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "==================================="
echo " PEA is starting up!"
echo "==================================="
echo ""
echo " Frontend:  http://localhost:3000"
echo " Backend:   http://localhost:8000"
echo " API Docs:  http://localhost:8000/docs"
echo " ChromaDB:  http://localhost:8100"
echo ""
echo " Press Ctrl+C to stop all services"
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker stop pea-chromadb 2>/dev/null" EXIT
wait
