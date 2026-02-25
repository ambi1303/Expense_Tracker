# Database Connection Fix

## Problem
The application was failing with "relation 'users' does not exist" error during OAuth callback, even though the database tables were properly created and migrations were applied.

## Root Cause
When running `uvicorn main:app --reload`, the reloader spawns worker processes that import modules before the `.env` file is loaded in `main.py`. The `app/database.py` module was trying to read `DATABASE_URL` at import time (module level) before the environment variables were loaded, causing connection failures.

## Solution Applied
Added `load_dotenv()` call directly in `backend/app/database.py` to ensure environment variables are loaded when the module is imported, regardless of import order.

## Changes Made

### 1. Fixed `backend/app/database.py`
- Added `from dotenv import load_dotenv` import
- Added `load_dotenv()` call before reading `DATABASE_URL`
- This ensures environment variables are available even when the module is imported by uvicorn worker processes

### 2. Added `backend/main.py` debug endpoint
- Added `/debug/db` endpoint to verify database connection from within the running application
- Useful for troubleshooting database connectivity issues

### 3. Created diagnostic scripts
- `backend/verify_and_fix_db.py` - Checks database state and table existence
- `backend/test_db_connection.py` - Tests database connection using app configuration

## What You Need to Do

### 1. Restart the Application
The server needs to be restarted for the changes to take effect:

```bash
# Stop the current server (Ctrl+C)
# Then restart:
cd backend
uvicorn main:app --reload
```

### 2. Test the OAuth Flow
1. Navigate to `http://localhost:8000/auth/google`
2. Complete the Google OAuth login
3. You should be redirected to the frontend with a session token
4. The user should be created/updated in the database

### 3. Verify Database Connection (Optional)
You can verify the database is working by visiting:
- `http://localhost:8000/debug/db` - Shows database connection status and table list

## Verification
After restarting, the OAuth flow should work without errors. The application will:
1. Successfully connect to the database
2. Query/create users in the `users` table
3. Store encrypted refresh tokens
4. Generate session JWT tokens
5. Redirect to the frontend

## Additional Notes
- The database tables (users, transactions, sync_logs) are confirmed to exist
- There is already 1 user in the database from a previous successful OAuth attempt
- All migrations are properly applied (version: ff4c1e7fcf3b)
- The fix ensures compatibility with uvicorn's --reload mode
