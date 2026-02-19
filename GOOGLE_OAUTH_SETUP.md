# Google OAuth Setup - Step by Step

## Current Configuration
Your app is configured to use:
- **Redirect URI**: `http://localhost:8000/auth/callback`
- **Client ID**: `857254970988-f1l74up3vdn0pv9iuo7pjsau26au65d4.apps.googleusercontent.com`

## Step-by-Step Fix

### 1. Open Google Cloud Console
Go to: https://console.cloud.google.com/apis/credentials

### 2. Find Your OAuth Client
Look for the OAuth 2.0 Client ID with ID starting with `857254970988-f1l74up3vdn0pv9iuo7pjsau26au65d4`

### 3. Click on the Client ID Name
This will open the configuration page

### 4. Add Authorized Redirect URI
In the "Authorized redirect URIs" section:
- Click "+ ADD URI"
- Enter EXACTLY: `http://localhost:8000/auth/callback`
- Make sure there's NO trailing slash
- Make sure it's `http://` not `https://`
- Make sure the port is `8000`

### 5. Save
Click the "SAVE" button at the bottom

### 6. Add Test User (if not already done)
Go to: https://console.cloud.google.com/apis/credentials/consent
- Scroll to "Test users"
- Click "+ ADD USERS"
- Add: `jhaambikesh555@gmail.com`
- Click "SAVE"

### 7. Wait 1-2 Minutes
Google needs a moment to propagate the changes

### 8. Try Again
- Go to http://localhost:5173
- Click "Continue with Google"
- You should now be able to log in!

## Troubleshooting

### If you still get redirect_uri_mismatch:
1. Double-check the URI is EXACTLY: `http://localhost:8000/auth/callback`
2. No extra spaces
3. No trailing slash
4. Correct port (8000)
5. Wait 1-2 minutes after saving

### If you get access_denied:
1. Make sure you added yourself as a test user
2. Make sure the OAuth consent screen is in "Testing" mode

### If you get "App not verified":
1. This is normal for development
2. Click "Advanced"
3. Click "Go to Expense Tracker (unsafe)"
4. This is safe - it's your own app

## What Should Happen After Login

1. You'll see Google's consent screen
2. Grant permissions for Gmail and profile access
3. You'll be redirected to: http://localhost:5173/dashboard
4. You should see the dashboard with 0 transactions
5. Click "Sync Now" to fetch your transaction emails

## Screenshot of What to Add

In Google Cloud Console > Credentials > Your OAuth Client:

```
Authorized redirect URIs
┌─────────────────────────────────────────────┐
│ http://localhost:8000/auth/callback         │  [X]
└─────────────────────────────────────────────┘
[+ ADD URI]
```

Make sure it looks exactly like this!
