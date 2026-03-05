#!/bin/bash
# Database initialization script for Image Rating Server

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Database Initialization${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# Change to backend directory
cd "$BACKEND_DIR"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}uv is not installed. Please install uv first.${NC}"
    echo "Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Run database initialization
echo -e "${YELLOW}Initializing database...${NC}"
uv run python -m app.db.init_db

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Database initialized successfully!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Default user created:"
echo -e "  Email:    ${YELLOW}demo@example.com${NC}"
echo -e "  Password: ${YELLOW}password123${NC}"
echo ""
