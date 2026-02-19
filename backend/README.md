# Gmail AI Expense Tracker - Backend

FastAPI backend for automated expense tracking via Gmail email analysis.

## Setup

### 1. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your configuration:

```bash
cp .env.example .env
```

Required variables:
- `DATABASE_URL`: Neon PostgreSQL connection string
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `GOOGLE_REDIRECT_URI`: OAuth callback URL
- `JWT_SECRET`: Secret key for JWT token generation
- `ENCRYPTION_KEY`: Fernet encryption key for refresh tokens
- `FRONTEND_URL`: Frontend application URL for CORS

### 4. Run Database Migrations

```bash
alembic upgrade head
```

### 5. Start Development Server

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## Project Structure

```
backend/
├── app/
│   ├── auth/          # Authentication & security modules
│   ├── models/        # SQLAlchemy database models
│   ├── routes/        # API route handlers
│   ├── schemas/       # Pydantic data validation schemas
│   ├── scheduler/     # Background job scheduling
│   └── services/      # Business logic services
├── alembic/           # Database migrations
├── tests/             # Test suite
├── main.py            # Application entry point
├── requirements.txt   # Python dependencies
└── .env.example       # Environment variable template
```

## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app --cov-report=html
```

## API Endpoints

- `GET /` - Health check
- `GET /docs` - OpenAPI documentation
- Authentication routes (to be implemented)
- Transaction routes (to be implemented)
- Analytics routes (to be implemented)
- Sync routes (to be implemented)
