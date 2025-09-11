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

echo "Starting backend server..."
# Start backend in the background. Use 'nohup' to keep it running after terminal closes.
# Redirect stdout/stderr to files to avoid cluttering the terminal.
nohup python backend/server.py > backend_output.log 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID. Logs in backend_output.log"

echo "Starting frontend server..."
# Start frontend in the foreground so you can see its output and use Ctrl+C to stop it.
# We'll open the browser to the URL with parameters after the server starts.
npm run dev --prefix frontend &
FRONTEND_PID=$!

# Wait a moment for the frontend server to start
sleep 5

# Open the browser with the preloaded parameters
x-www-browser "$FRONTEND_URL" 2>/dev/null || open "$FRONTEND_URL" 2>/dev/null || echo "Please open your browser to: $FRONTEND_URL"

wait $FRONTEND_PID

# When npm run dev exits (e.g., by Ctrl+C), kill the backend process
echo "Frontend server stopped. Killing backend process (PID: $BACKEND_PID)..."
kill $BACKEND_PID

echo "Development environment shut down."