# API Quick Reference

## 🚀 Access Points

| Interface | URL | Purpose |
|-----------|-----|---------|
| **Swagger UI** | http://localhost:8000/docs | Interactive API testing |
| **ReDoc** | http://localhost:8000/redoc | Clean documentation |
| **OpenAPI JSON** | http://localhost:8000/openapi.json | API specification |

## 📋 Endpoints Overview

### 🏥 Health (No Auth Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/debug/db` | Database connection status |

### 🔐 Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/auth/google` | ❌ | Initiate OAuth login |
| GET | `/auth/callback` | ❌ | OAuth callback (auto) |
| POST | `/auth/set-session` | ❌ | Set session cookie |
| GET | `/auth/me` | ✅ | Get current user profile |
| POST | `/auth/logout` | ✅ | Logout and clear session |

### 💰 Transactions

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/transactions` | ✅ | List transactions (paginated) |
| GET | `/transactions/export` | ✅ | Export transactions as CSV |

**Query Parameters for `/transactions`:**
- `skip` (int): Pagination offset (default: 0)
- `limit` (int): Items per page (default: 50, max: 100)
- `transaction_type` (string): Filter by "debit" or "credit"
- `start_date` (string): Filter from date (YYYY-MM-DD)
- `end_date` (string): Filter to date (YYYY-MM-DD)
- `merchant` (string): Filter by merchant name
- `bank_name` (string): Filter by bank
- `min_amount` (decimal): Minimum amount
- `max_amount` (decimal): Maximum amount

### 📊 Analytics

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/analytics/summary` | ✅ | Overall spending summary |
| GET | `/analytics/monthly` | ✅ | Monthly spending trends |
| GET | `/analytics/categories` | ✅ | Spending by merchant/category |

**Query Parameters:**
- `/analytics/monthly?months=6` - Number of months (1-24)
- `/analytics/categories?limit=10` - Top N categories (1-50)

### 🔄 Sync

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/sync/manual` | ✅ | Trigger email sync now |
| GET | `/sync/history` | ✅ | View sync log history |

**Query Parameters for `/sync/history`:**
- `limit` (int): Number of logs (default: 20, max: 100)

## 🔑 Authentication Flow

```
1. User → GET /auth/google
2. Browser → Google OAuth consent screen
3. User approves
4. Google → GET /auth/callback?code=...
5. Backend → Creates/updates user, sets session cookie
6. Browser → Redirected to frontend with token
7. Frontend → POST /auth/set-session (sets HTTPOnly cookie)
8. User is authenticated! 🎉
```

## 📝 Example Requests

### Using curl

```bash
# Health check
curl http://localhost:8000/

# Database status
curl http://localhost:8000/debug/db

# Get user profile (with auth cookie)
curl http://localhost:8000/auth/me \
  -H "Cookie: session_token=YOUR_TOKEN"

# List transactions with filters
curl "http://localhost:8000/transactions?transaction_type=debit&limit=10" \
  -H "Cookie: session_token=YOUR_TOKEN"

# Trigger manual sync
curl -X POST http://localhost:8000/sync/manual \
  -H "Cookie: session_token=YOUR_TOKEN"

# Get analytics summary
curl http://localhost:8000/analytics/summary \
  -H "Cookie: session_token=YOUR_TOKEN"

# Export transactions
curl http://localhost:8000/transactions/export \
  -H "Cookie: session_token=YOUR_TOKEN" \
  -o transactions.csv
```

### Using Python requests

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000"

# Session to maintain cookies
session = requests.Session()

# After OAuth login, cookie is set automatically
# Get user profile
response = session.get(f"{BASE_URL}/auth/me")
user = response.json()
print(f"Logged in as: {user['name']}")

# Trigger sync
response = session.post(f"{BASE_URL}/sync/manual")
sync_result = response.json()
print(f"Synced {sync_result['transactions_added']} new transactions")

# Get transactions
response = session.get(f"{BASE_URL}/transactions", params={
    "transaction_type": "debit",
    "limit": 10
})
data = response.json()
print(f"Found {data['total']} transactions")

# Get analytics
response = session.get(f"{BASE_URL}/analytics/summary")
summary = response.json()
print(f"Total spent: {summary['total_spent']}")
```

### Using JavaScript fetch

```javascript
// Get user profile
const response = await fetch('http://localhost:8000/auth/me', {
  credentials: 'include' // Include cookies
});
const user = await response.json();
console.log('Logged in as:', user.name);

// Trigger sync
const syncResponse = await fetch('http://localhost:8000/sync/manual', {
  method: 'POST',
  credentials: 'include'
});
const syncResult = await syncResponse.json();
console.log('Synced transactions:', syncResult.transactions_added);

// Get transactions with filters
const txResponse = await fetch(
  'http://localhost:8000/transactions?transaction_type=debit&limit=10',
  { credentials: 'include' }
);
const txData = await txResponse.json();
console.log('Transactions:', txData.transactions);
```

## 🎯 Common Use Cases

### 1. First Time Setup
```
GET /debug/db              → Verify database
GET /auth/google           → Login
GET /auth/me               → Confirm auth
POST /sync/manual          → Fetch emails
GET /transactions          → View results
```

### 2. Daily Check
```
GET /auth/me               → Still logged in?
POST /sync/manual          → Get new emails
GET /analytics/summary     → Quick overview
```

### 3. Monthly Review
```
GET /analytics/monthly?months=1    → This month's spending
GET /analytics/categories          → Where did money go?
GET /transactions/export           → Download for records
```

### 4. Detailed Analysis
```
GET /transactions?start_date=2026-01-01&end_date=2026-01-31
GET /transactions?merchant=Amazon
GET /transactions?min_amount=1000
GET /analytics/categories?limit=20
```

## 🔒 Security Notes

- Session cookies are **HTTPOnly** (not accessible via JavaScript)
- Cookies are **Secure** in production (HTTPS only)
- Cookies use **SameSite=Lax** (CSRF protection)
- Session expires after **7 days**
- Refresh tokens are **encrypted** in database
- OAuth uses **PKCE** flow for security

## 📊 Response Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | Success | Request completed successfully |
| 307 | Redirect | OAuth flow redirect |
| 400 | Bad Request | Invalid parameters or data |
| 401 | Unauthorized | Not logged in or session expired |
| 404 | Not Found | Endpoint doesn't exist |
| 422 | Validation Error | Request data doesn't match schema |
| 500 | Server Error | Backend error (check logs) |

## 🐛 Debugging Tips

1. **Check server logs** - Terminal shows detailed errors
2. **Use /debug/db** - Verify database connection
3. **Test /auth/me** - Confirm authentication works
4. **Check browser cookies** - DevTools → Application → Cookies
5. **Try Swagger UI** - Interactive testing at /docs
6. **Review response body** - Error messages explain issues
7. **Check query params** - Ensure correct format (dates, numbers)

## 📚 Additional Resources

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Full Guide**: See `SWAGGER_GUIDE.md`
- **Fix Summary**: See `FIX_SUMMARY.md`

---

**Need help?** Check the Swagger UI at http://localhost:8000/docs for interactive examples!
