#!/bin/bash
# Ubuntu deployment script for Image Rating Server (using uv)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="image-rating-server"
DEPLOY_DIR="/opt/$APP_NAME"
BACKEND_DIR="$DEPLOY_DIR/backend"
FRONTEND_DIR="$DEPLOY_DIR/frontend"
SERVICE_FILE="/etc/systemd/system/$APP_NAME-backend.service"
FRONTEND_SERVICE_FILE="/etc/systemd/system/$APP_NAME-frontend.service"

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Image Rating Server Deployment Script${NC}"
echo -e "${GREEN}Using uv for Python package management${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run this script as root (use sudo)${NC}"
    exit 1
fi

# Check if Ubuntu
if [ ! -f /etc/os-release ] || ! grep -q "ubuntu" /etc/os-release; then
    echo -e "${YELLOW}Warning: This script is designed for Ubuntu${NC}"
fi

# Install system dependencies
echo -e "${YELLOW}Installing system dependencies...${NC}"
apt-get update
apt-get install -y curl python3.11 python3.11-venv nodejs npm nginx

# Install uv
echo -e "${YELLOW}Installing uv package manager...${NC}"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Create deployment directory
echo -e "${YELLOW}Setting up deployment directory...${NC}"
mkdir -p "$DEPLOY_DIR"
# Copy files (assuming script is run from project directory)
# In production, you might want to git clone instead
# cp -r ./* "$DEPLOY_DIR/"

# Setup backend with uv
echo -e "${YELLOW}Setting up backend with uv...${NC}"
cd "$BACKEND_DIR"

# Sync dependencies with uv
uv sync --no-dev

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env with your configuration!${NC}"
fi

# Setup frontend
echo -e "${YELLOW}Setting up frontend...${NC}"
cd "$FRONTEND_DIR"
npm install
npm run build

# Create systemd service for backend (using uv run)
echo -e "${YELLOW}Creating systemd services...${NC}"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Image Rating Server Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$BACKEND_DIR
Environment="PATH=/root/.local/bin:\$PATH"
ExecStart=$(which uv) run uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for frontend
cat > "$FRONTEND_SERVICE_FILE" << EOF
[Unit]
Description=Image Rating Server Frontend
After=network.target backend.service

[Service]
Type=simple
User=www-data
WorkingDirectory=$FRONTEND_DIR
ExecStart=$(which npm) start -- -p 8081
Restart=always
RestartSec=10
Environment="NODE_ENV=production"

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
chown -R www-data:www-data "$DEPLOY_DIR"

# Enable and start services
echo -e "${YELLOW}Starting services...${NC}"
systemctl daemon-reload
systemctl enable "$APP_NAME-backend.service"
systemctl enable "$APP_NAME-frontend.service"
systemctl start "$APP_NAME-backend.service"
systemctl start "$APP_NAME-frontend.service"

# Setup Nginx reverse proxy (optional)
echo -e "${YELLOW}Setting up Nginx configuration...${NC}"
cat > "/etc/nginx/sites-available/$APP_NAME" << EOF
server {
    listen 80;
    server_name _;

    # Frontend
    location / {
        proxy_pass http://localhost:8081;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
ln -sf "/etc/nginx/sites-available/$APP_NAME" "/etc/nginx/sites-enabled/"
systemctl reload nginx

# Display status
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Backend status: ${YELLOW}systemctl status $APP_NAME-backend${NC}"
echo -e "Frontend status: ${YELLOW}systemctl status $APP_NAME-frontend${NC}"
echo -e "View logs: ${YELLOW}journalctl -u $APP_NAME-backend -f${NC}"
echo ""
echo -e "Services:"
echo -e "  Backend:  ${YELLOW}http://localhost:8080${NC}"
echo -e "  Frontend: ${YELLOW}http://localhost:8081${NC}"
echo -e "  Nginx:    ${YELLOW}http://localhost${NC}"
echo ""
echo -e "${RED}Remember to:${NC}"
echo -e "  1. Edit $BACKEND_DIR/.env with your settings"
echo -e "  2. Set up a proper domain name"
echo -e "  3. Configure SSL/TLS with Let's Encrypt"
echo ""
