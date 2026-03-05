#!/bin/bash
# Development startup script - runs both frontend and backend

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}Starting Image Rating Server Development Environment${NC}"
echo "Project directory: $PROJECT_DIR"

# Function to cleanup processes on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping all processes...${NC}"
    jobs -p | xargs -r kill 2>/dev/null
    wait 2>/dev/null
    echo -e "${GREEN}All processes stopped.${NC}"
    exit 0
}

# Trap SIGINT and SIGTERM
trap cleanup SIGINT SIGTERM

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}uv is not installed. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Sync backend dependencies with uv
echo -e "${YELLOW}Installing backend dependencies with uv...${NC}"
cd "$PROJECT_DIR/backend"
uv sync

# Check if node_modules exists
if [ ! -d "$PROJECT_DIR/frontend/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd "$PROJECT_DIR/frontend"
    npm install
    cd "$PROJECT_DIR"
fi

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/backend/logs"

# Start backend server in background using uv run
echo -e "${GREEN}Starting backend server on port 8080...${NC}"
cd "$PROJECT_DIR/backend"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend server in background
echo -e "${GREEN}Starting frontend server on port 8081...${NC}"
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Display status
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Development servers are running!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Backend API: ${YELLOW}http://localhost:8080${NC}"
echo -e "API Docs:    ${YELLOW}http://localhost:8080/docs${NC}"
echo -e "Frontend:    ${YELLOW}http://localhost:8081${NC}"
echo ""
echo -e "Press ${YELLOW}Ctrl+C${NC} to stop all servers."
echo ""

# Wait for any background process to finish
wait
