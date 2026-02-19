# Fix OAuth Redirect URI Mismatch

## The Problem
Error: `redirect_uri_mismatch` - The redirect URI in your request doesn't match what's configured in Google Cloud Console.

## The Solution

### Step 1: Go to Google Cloud Console
1. Visit: https://console.cloud.google.com/
2. Select your project (or create a new one)

### Step 2: Enable Gmail API
1. Go to "APIs & Services" > "Library"
2. Search for "Gmail API"
3. Click "Enable"

### Step 3: Configure OAuth Consent Screen
1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type
3. Fill in:
   - App name: Gmail Expense Tracker
   - User support email: your email
   - Developer contact: your email
4. Click "Save and Continue"
5. Add scopes:
   - `.../auth/gmail.readonly`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
6. Click "Save and Continue"
7. Add test users (your Gmail address)
8. Click "Save and Continue"

### Step 4: Create OAuth Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Web application"
4. Name it: "Gmail Expense Tracker Web Client"
5. **IMPORTANT**: Add Authorized redirect URIs:
   ```
   http://localhost:8000/auth/callback
   ```
6. Click "Create"
7. Copy the Client ID and Client Secret

### Step 5: Update Backend .env File
Replace the values in `backend/.env`:

```env
GOOGLE_CLIENT_ID=your_new_client_id_here
GOOGLE_CLIENT_SECRET=your_new_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
```

### Step 6: Restart Backend Server
1. Stop the current backend server (Ctrl+C)
2. Start it again:
   ```bash
   cd backend
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Current Configuration

Your backend expects:
- **Redirect URI**: `http://localhost:8000/auth/callback`

This MUST match exactly in Google Cloud Console.

## Testing

After updating:
1. Go to http://localhost:5173
2. Click "Continue with Google"
3. You should see the Google consent screen
4. After authorizing, you'll be redirected to the dashboard

## Common Issues

### Issue: Still getting redirect_uri_mismatch
- Make sure the URI is EXACTLY: `http://localhost:8000/auth/callback`
- No trailing slash
- Must be http (not https) for localhost
- Port must be 8000

### Issue: App not verified warning
- This is normal for development
- Click "Advanced" > "Go to Gmail Expense Tracker (unsafe)"
- This only appears because the app is in testing mode

### Issue: Access blocked
- Make sure you added your email as a test user in OAuth consent screen
- The app must be in "Testing" mode to allow test users

## Production Deployment

When deploying to production:
1. Add your production redirect URI:
   ```
   https://yourdomain.com/auth/callback
   ```
2. Update GOOGLE_REDIRECT_URI in production environment
3. Publish the OAuth consent screen (requires verification)
