# Gmail Expense Tracker - Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL database (Neon recommended)
- Google Cloud Project with Gmail API enabled

## Backend Setup

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

4. Configure environment variables in `.env`:
```
DATABASE_URL=postgresql://user:password@host/database
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
JWT_SECRET=your_jwt_secret
ENCRYPTION_KEY=your_encryption_key
FRONTEND_URL=http://localhost:5173
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the backend server:
```bash
uvicorn main:app --reload
```

Backend will be available at http://localhost:8000

## Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment variables in `.env`:
```
VITE_API_URL=http://localhost:8000
```

4. Start the development server:
```bash
npm run dev
```

Frontend will be available at http://localhost:5173

## Google OAuth Setup

1. Go to Google Cloud Console
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: http://localhost:8000/auth/callback
6. Copy Client ID and Client Secret to backend .env

## Testing

Backend tests:
```bash
cd backend
pytest
```

Frontend build:
```bash
cd frontend
npm run build
```

## Features

- Google OAuth authentication
- Automatic Gmail transaction email parsing
- Dashboard with analytics and charts
- Transaction filtering and pagination
- CSV export
- Dark mode
- Automatic sync every 15 minutes
