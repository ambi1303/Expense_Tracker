# Fix Gmail Scope Issue

## The Problem

Error: `Scope has changed from "...gmail.readonly" to "..."`

This means you authorized the app, but **didn't grant Gmail access**. The app needs Gmail access to read your transaction emails.

## Why This Happened

One of these reasons:
1. ❌ Gmail API not enabled in Google Cloud
2. ❌ Gmail scope not added to OAuth consent screen
3. ❌ You clicked "Deny" for Gmail during authorization

## Solution

### Step 1: Enable Gmail API

1. Go to: https://console.cloud.google.com/apis/library
2. Search for "Gmail API"
3. Click on it
4. Click "ENABLE"

### Step 2: Add Gmail Scope to OAuth Consent Screen

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Click "EDIT APP"
3. Click "SAVE AND CONTINUE" on App information
4. On "Scopes" page, click "ADD OR REMOVE SCOPES"
5. In the filter, search for "gmail"
6. Check the box for:
   - `.../auth/gmail.readonly` - Read all resources and their metadata—no write operations
7. Also make sure these are checked:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`  
   - `openid`
8. Click "UPDATE"
9. Click "SAVE AND CONTINUE"
10. Click "SAVE AND CONTINUE" on Test users
11. Click "BACK TO DASHBOARD"

### Step 3: Revoke Previous Authorization

Since you already authorized without Gmail, you need to revoke and re-authorize:

1. Go to: https://myaccount.google.com/permissions
2. Find "Expense Tracker" or your app name
3. Click on it
4. Click "Remove Access"

### Step 4: Try Logging In Again

1. Go to: http://localhost:5173
2. Click "Continue with Google"
3. You should now see a consent screen asking for:
   - ✅ View your email address
   - ✅ See your personal info
   - ✅ **Read your Gmail messages** ← This is the important one!
4. Make sure to click "Allow" for all permissions
5. You'll be redirected to the dashboard

## What You Should See

On the Google consent screen, you should see:

```
Expense Tracker wants to access your Google Account

This will allow Expense Tracker to:
✓ Read your Gmail messages and settings
✓ See your primary Google Account email address
✓ See your personal info, including any personal info you've made publicly available

[Cancel] [Allow]
```

Make sure you click **Allow** for all of them!

## After Successful Login

Once you grant all permissions:
1. You'll be redirected to the dashboard
2. Click "Sync Now" to fetch transaction emails
3. The app will parse your bank transaction emails
4. Transactions will appear in the dashboard and transactions page

## Troubleshooting

### "Gmail API has not been used in project"
- Go to APIs & Services > Library
- Search "Gmail API"
- Click Enable

### Still getting scope error
- Make sure you revoked the old authorization
- Clear browser cookies for localhost
- Try in incognito/private mode

### "This app isn't verified"
- This is normal for development
- Click "Advanced"
- Click "Go to Expense Tracker (unsafe)"
- It's safe - it's your own app!
