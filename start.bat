@echo off
REM PEA - Personal Experience Amplifier
REM Windows startup script

echo ===================================
echo  PEA - Personal Experience Amplifier
echo ===================================
echo.

if not exist .env (
    echo [!] No .env file found.
    echo     Copying .env.example to .env...
    copy .env.example .env
    echo     [!] Please edit .env and set your LLM API key.
    echo     Required: DEEPSEEK_API_KEY
    pause
    exit /b 1
)

echo [1/4] Initializing database...
cd backend
python init_db.py
cd ..

echo [2/4] Starting ChromaDB...
docker run -d --name pea-chromadb -p 8100:8000 -v chroma_data:/chroma/chroma chromadb/chroma:latest 2>nul || echo   ChromaDB container already running

echo [3/4] Starting backend...
start "PEA Backend" cmd /c "cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [4/4] Starting frontend...
start "PEA Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo ===================================
echo  PEA is starting up!
echo ===================================
echo.
echo  Frontend:  http://localhost:3000
echo  Backend:   http://localhost:8000
echo  API Docs:  http://localhost:8000/docs
echo  ChromaDB:  http://localhost:8100
echo.
echo  Close this window to stop.
pause
