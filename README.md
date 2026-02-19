# Gmail Expense Tracker

A full-stack application for tracking expenses from Gmail receipts using Google OAuth authentication.

## Features

- Google OAuth authentication
- Gmail integration for expense tracking
- PostgreSQL database with async support
- JWT-based session management
- Encrypted sensitive data storage
- Property-based testing with Hypothesis

## Tech Stack

### Backend
- FastAPI (Python)
- PostgreSQL with asyncpg
- SQLAlchemy ORM
- Alembic for migrations
- Google OAuth 2.0
- Cryptography (Fernet encryption)

### Frontend
- React with Vite
- Axios for API calls
- Modern UI components

## Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL database
- Google OAuth credentials

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the server:
```bash
uvicorn app.main:app --reload
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

## Environment Variables

See `backend/.env.example` for required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `JWT_SECRET`: Secret key for JWT tokens
- `ENCRYPTION_KEY`: Fernet encryption key
- `FRONTEND_URL`: Frontend application URL

## Production Deployment

### Important Security Notes

1. **Never commit `.env` files** - they contain sensitive credentials
2. **Rotate all secrets** before production deployment
3. **Use environment-specific configurations**
4. **Enable HTTPS** for all production endpoints
5. **Update CORS settings** for production domains

### Production Checklist

- [ ] Update `ENVIRONMENT=production` in `.env`
- [ ] Generate new `JWT_SECRET` (minimum 32 characters)
- [ ] Generate new `ENCRYPTION_KEY` using Fernet
- [ ] Update `GOOGLE_REDIRECT_URI` to production URL
- [ ] Update `FRONTEND_URL` to production domain
- [ ] Configure production database
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS for production domain
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR`
- [ ] Run database migrations on production
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy

## Testing

Run backend tests:
```bash
cd backend
pytest
```

Run property-based tests:
```bash
pytest tests/test_property_*.py
```

## License

MIT
