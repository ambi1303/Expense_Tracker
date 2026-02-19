# Connection Test Guide

## Current Status

✅ **Backend**: Running on http://localhost:8000
✅ **Frontend**: Running on http://localhost:5173
✅ **CORS**: Configured correctly
✅ **Authentication**: Ready

## Expected Behavior

### 1. Initial Load (401 Error is NORMAL)
When you first visit http://localhost:5173:
- The frontend tries to check authentication by calling `/auth/me`
- Since you're not logged in, it returns **401 Unauthorized**
- This is EXPECTED and CORRECT behavior
- The frontend should automatically redirect you to `/login`

### 2. Login Flow
1. Visit http://localhost:5173
2. You should see the Login page with "Continue with Google" button
3. Click the button
4. You'll be redirected to Google OAuth consent screen
5. After authorizing, you'll be redirected back to the dashboard

### 3. After Login
Once authenticated:
- Dashboard should load with summary cards (will show 0 transactions initially)
- You can click "Sync Now" to fetch emails from Gmail
- Transactions page will show your parsed transactions
- Settings page will show your account info

## Testing Steps

1. **Open Browser**: Navigate to http://localhost:5173
   - Expected: Login page appears

2. **Check Browser Console**: 
   - You should see a 401 error for `/auth/me` - this is NORMAL
   - The app should redirect to `/login`

3. **Click "Continue with Google"**:
   - Expected: Redirect to Google OAuth
   - Grant permissions
   - Redirect back to dashboard

4. **Test Dashboard**:
   - Should show summary cards (0 transactions initially)
   - Click "Sync Now" to fetch emails

5. **Test Transactions Page**:
   - Navigate to Transactions
   - Should show empty state or synced transactions

## Troubleshooting

### If you see 401 errors:
- ✅ This is NORMAL before login
- ❌ If you see 401 AFTER login, check:
  - Browser cookies are enabled
  - Cookie is being set (check DevTools > Application > Cookies)

### If OAuth fails:
- Check Google OAuth credentials in backend/.env
- Verify redirect URI matches: http://localhost:8000/auth/callback

### If CORS errors appear:
- Backend CORS is configured for http://localhost:5173
- Make sure frontend is running on port 5173

## API Endpoints

Test these in your browser or Postman:

- `GET http://localhost:8000/` - Health check (should return 200)
- `GET http://localhost:8000/docs` - API documentation
- `GET http://localhost:8000/auth/google` - Start OAuth flow
- `GET http://localhost:8000/auth/me` - Get current user (requires auth)

## Current Setup

Backend Environment:
- Database: Neon PostgreSQL (configured)
- Google OAuth: Configured with your credentials
- JWT Secret: Generated
- Encryption Key: Generated

Frontend Environment:
- API URL: http://localhost:8000
- Axios configured with credentials: true
- Cookie-based authentication

## Next Steps

1. Open http://localhost:5173 in your browser
2. You should see the login page
3. Click "Continue with Google"
4. Authorize the application
5. You'll be redirected to the dashboard
6. Click "Sync Now" to fetch your transaction emails

The 401 error you're seeing is completely normal and expected - it just means you need to log in first!
