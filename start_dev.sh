#!/bin/bash

# Navigate to the project root (where this script is located)
cd "$(dirname "$0")"

echo "Activating virtual environment..."
source my-venv/bin/activate

if [ $? -ne 0 ]; then
    echo "Error: Could not activate virtual environment. Please ensure 'my-venv' exists and is correctly set up."
    exit 1
fi

# Default testing parameters
PGN_FILE="/home/dev/Documents/ChessDB/Nakamura_chess_com_games_2025-09-07.pgn"
OUTPUT_FILE="/home/dev/Documents/ChessDB/TESTepd1.epd"
WORKERS="2"
MIN_ELO="1400"
MAX_PLY="4"

# Construct the frontend URL with query parameters
FRONTEND_URL="http://localhost:5173/?pgnFile=${PGN_FILE}&outputFile=${OUTPUT_FILE}&workers=${WORKERS}&minElo=${MIN_ELO}&maxPly=${MAX_PLY}"

echo "Ensuring required ports are free..."
# Use fuser to kill any process using TCP port 8000 (backend) and 5173 (frontend). This is more reliable than pkill.
fuser -k 8000/tcp 2>/dev/null
fuser -k 5173/tcp 2>/dev/null
sleep 1 # Give it a moment to die

echo "Starting backend server in stable mode..."
# We run uvicorn WITHOUT --reload. The --reload flag is unstable with the
# multiprocessing library and causes the server to crash. For backend changes,
# you will need to stop (Ctrl+C) and restart this script. This ensures stability.
uvicorn backend.server:app --host 127.0.0.1 --port 8000 > backend_output.log 2>&1 &
BACKEND_PID=$!

# Wait a moment and check if the server started successfully
sleep 3 # Give the server a moment to potentially fail
if ! ps -p $BACKEND_PID > /dev/null; then
    echo "Error: Backend server failed to start or crashed immediately. Check backend_output.log for details."
    exit 1
elif grep -q "address already in use" backend_output.log; then
    echo "Error: Backend server failed to start: Port 8000 is already in use."
    echo "Please make sure no other process is using that port and try again."
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo "Backend started with PID: $BACKEND_PID. Logs in backend_output.log"

echo "Starting frontend server..."
# Start frontend in the foreground so you can see its output and use Ctrl+C to stop it.
# We'll open the browser to the URL with parameters after the server starts.
npm run dev --prefix frontend &
FRONTEND_PID=$!

# Wait a moment for the frontend server to start
sleep 5

# Open the browser with the preloaded parameters
xdg-open "$FRONTEND_URL" 2>/dev/null || echo "Could not automatically open browser. Please open it to: $FRONTEND_URL"

# --- Cleanup Logic ---
cleanup() {
    echo "Shutting down development environment..."
    kill $FRONTEND_PID 2>/dev/null
    kill $BACKEND_PID 2>/dev/null
    echo "Shutdown complete."
}

# Trap the EXIT signal to ensure cleanup runs, no matter how the script is stopped.
trap cleanup EXIT

wait $FRONTEND_PID