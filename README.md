# Image Rating Server

Enterprise-level full-stack application for image rating and management, built with FastAPI (backend) and Next.js (frontend).

## Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **uv** - Fast Python package installer and resolver (100x faster than pip)
- **Pydantic** - Data validation using Python type annotations
- **JWT** - JSON Web Token authentication
- **Uvicorn** - ASGI server
- **SQLAlchemy** - SQL toolkit and ORM
- **Loguru** - Python logging made easy

### Frontend
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - Beautiful and accessible component library
- **Framer Motion** - Production-ready animation library
- **Zustand** - Small, fast and scalable state management

## Project Structure

```
image-rating-server/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API routes
│   │   │   ├── deps.py        # Dependency injection
│   │   │   └── v1/            # API v1 endpoints
│   │   ├── core/              # Core configuration
│   │   │   ├── config.py      # Settings management
│   │   │   ├── security.py    # JWT & password hashing
│   │   │   ├── logger.py      # Logging setup
│   │   │   └── database.py    # Database setup
│   │   ├── models/            # Database models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── utils/             # Utility functions
│   │   └── main.py            # Application entry point
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/                   # Next.js frontend
│   ├── src/
│   │   ├── app/               # App Router pages
│   │   │   ├── (auth)/        # Auth pages (login, register)
│   │   │   ├── (dashboard)/   # Protected pages
│   │   │   ├── layout.tsx
│   │   │   └── globals.css
│   │   ├── components/        # React components
│   │   │   └── ui/            # shadcn/ui components
│   │   ├── lib/               # Utilities
│   │   │   ├── api.ts         # API client
│   │   │   ├── auth.ts        # Auth utilities
│   │   │   └── utils.ts
│   │   ├── hooks/             # Custom hooks
│   │   ├── providers/         # Context providers
│   │   ├── store/             # Zustand stores
│   │   └── types/             # TypeScript types
│   ├── components.json        # shadcn/ui config
│   ├── package.json
│   └── next.config.ts
│
├── scripts/                    # Utility scripts
│   ├── dev.sh                 # Development startup
│   └── deploy.sh              # Ubuntu deployment
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn
- uv (Python package manager) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd image-rating-server
   ```

2. **Backend setup (using uv)**
   ```bash
   cd backend
   uv sync                    # Install dependencies
   cp .env.example .env       # Edit .env with your configuration
   ```

3. **Frontend setup**
   ```bash
   cd frontend
   npm install
   cp .env.local.example .env.local  # Edit with your configuration
   npm run build  # Optional: Build for production
   ```

### Running the Application

#### Development Mode

**Option 1: Using the dev script**

Linux/Mac:
```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

Windows:
```bat
scripts\dev.bat
```

**Option 2: Manual startup**

Terminal 1 - Backend:
```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

#### Production Mode

**Backend:**
```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4
```

**Frontend:**
```bash
cd frontend
npm run build
npm start
```

### Access Points

- **Frontend**: http://localhost:8081
- **Backend API**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Get current user

### Users
- `GET /api/v1/users/me` - Get user profile
- `PATCH /api/v1/users/me` - Update profile
- `POST /api/v1/users/me/change-password` - Change password
- `GET /api/v1/users/` - List users (admin)
- `GET /api/v1/users/{user_id}` - Get user by ID

## Demo Credentials

For testing the authentication flow:
- **Email**: demo@example.com
- **Password**: password123

## Deployment

### Ubuntu Server Deployment

The `scripts/deploy.sh` script automates deployment on Ubuntu:

```bash
sudo ./scripts/deploy.sh
```

This will:
1. Install system dependencies (Python, Node.js, Nginx)
2. Set up the backend with virtual environment
3. Build the frontend
4. Create systemd services
5. Configure Nginx reverse proxy

### Manual Deployment

1. **Backend as systemd service**
   ```bash
   sudo cp scripts/backend.service /etc/systemd/system/
   sudo systemctl enable image-rating-backend
   sudo systemctl start image-rating-backend
   ```

2. **Frontend with PM2**
   ```bash
   npm install -g pm2
   cd frontend
   pm2 start npm --name "image-rating-frontend" -- start
   pm2 save
   pm2 startup
   ```

## Configuration

### Backend Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | 30 |
| `FRONTEND_URL` | Frontend URL for CORS | http://localhost:8081 |
| `DATABASE_URL` | Database connection | sqlite+aiosqlite:///./app.db |

### Frontend Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | http://localhost:8080 |

## Development Tools

### Backend
- **uv** - Fast Python package manager (100x faster than pip)
- **Black** - Code formatting
- **Ruff** - Fast Python linter
- **MyPy** - Static type checking
- **Pytest** - Testing framework

#### Common uv Commands

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras

# Run a command in the uv environment
uv run python script.py
uv run uvicorn app.main:app

# Add a new dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Run tests
uv run pytest
```

### Frontend
- **ESLint** - JavaScript/TypeScript linting
- **Prettier** - Code formatting
- **TypeScript** - Type checking

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
