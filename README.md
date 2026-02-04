# AI-Academy 3 ATI Stats

A system to track, analyze, and report on how Public Bodies process Access to Information (ATI) requests.

## Features

- Track ATI request submissions and responses
- Analyze response times and compliance rates
- Generate statistical reports and visualizations
- Compare performance across public bodies
- Export data in multiple formats (PDF, CSV, Excel)

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0
- **Testing**: Pytest

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for local database)
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ati-stats
   ```

2. **Create and activate virtual environment**
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate (Linux/macOS)
   source .venv/bin/activate
   
   # Activate (Windows)
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env with your settings
   ```

5. **Start local services (PostgreSQL, Redis)**
   ```bash
   docker-compose up -d
   ```

6. **Run the development server**
   ```bash
   make run
   # or
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the application**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/v1/docs
   - Health Check: http://localhost:8000/health

### Development Commands

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Format code
make format

# Run linting
make lint

# Clean cache files
make clean

# Stop Docker services
make docker-down
```

### Optional: pgAdmin

To start with pgAdmin for database management:
```bash
make docker-up-tools
```
Access pgAdmin at http://localhost:5050 (admin@ati-stats.local / admin)

## Project Structure

```
ati-stats/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   └── core/
│       ├── __init__.py
│       └── config.py        # Application configuration
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   └── test_health.py       # Health check tests
├── .env.example             # Environment template
├── .gitignore
├── docker-compose.yml       # Local development services
├── Makefile                 # Development commands
├── pyproject.toml           # Project configuration
├── requirements.txt         # Python dependencies
├── PP.md                    # Project Plan
├── ProjectStatus.md         # Project Status Tracker
└── README.md
```

## API Documentation

Once the server is running, access the interactive API documentation:
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## License

This project is part of AI-Academy 3.

---

*Last Updated: Phase 3.1 - Development Environment Setup Complete*

