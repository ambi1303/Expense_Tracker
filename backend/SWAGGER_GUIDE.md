# Swagger UI Testing Guide

## Accessing Swagger UI

Your FastAPI application comes with **two** interactive API documentation interfaces:

### 1. Swagger UI (Recommended for Testing)
**URL**: http://localhost:8000/docs

Features:
- Interactive API testing
- Try out endpoints directly in the browser
- View request/response schemas
- See example values
- Test authentication flows

### 2. ReDoc (Better for Reading)
**URL**: http://localhost:8000/redoc

Features:
- Clean, readable documentation
- Better for understanding API structure
- No interactive testing
- Great for sharing with team members

## Quick Start

1. **Start the server** (if not already running):
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Open Swagger UI**:
   Navigate to http://localhost:8000/docs in your browser

3. **You should see**:
   - API title and description
   - List of all endpoints organized by tags
   - Health, Authentication, Transactions, Analytics, and Sync sections

## Testing Endpoints

### Step 1: Test Health Endpoints (No Auth Required)

1. **Health Check**:
   - Click on `GET /` under "Health" section
   - Click "Try it out"
   - Click "Execute"
   - You should see: `{"status": "healthy", ...}`

2. **Database Status**:
   - Click on `GET /debug/db` under "Health" section
   - Click "Try it out"
   - Click "Execute"
   - You should see database connection info and table list

### Step 2: Authenticate (Required for Most Endpoints)

**Important**: OAuth flow requires browser redirects, so you can't complete it entirely in Swagger UI.

**Option A: Use Browser for OAuth (Recommended)**
1. Open a new tab: http://localhost:8000/auth/google
2. Complete Google OAuth login
3. You'll be redirected to frontend with a session cookie set
4. Return to Swagger UI - you're now authenticated!

**Option B: Manual Cookie Setup (Advanced)**
1. Complete OAuth flow in browser (Option A)
2. Open browser DevTools → Application → Cookies
3. Copy the `session_token` cookie value
4. In Swagger UI, you can't directly set cookies, but the cookie will persist from your browser session

### Step 3: Test Authenticated Endpoints

Once authenticated, try these endpoints:

1. **Get Your Profile**:
   - `GET /auth/me`
   - Click "Try it out" → "Execute"
   - Should return your user profile

2. **Trigger Manual Sync**:
   - `POST /sync/manual`
   - Click "Try it out" → "Execute"
   - Fetches latest emails from Gmail

3. **List Transactions**:
   - `GET /transactions`
   - Adjust query parameters (skip, limit, filters)
   - Click "Execute"
   - View your expense transactions

4. **Get Analytics Summary**:
   - `GET /analytics/summary`
   - Click "Try it out" → "Execute"
   - See spending statistics

5. **Monthly Analytics**:
   - `GET /analytics/monthly`
   - Set `months` parameter (e.g., 6)
   - Click "Execute"
   - View monthly spending trends

6. **Category Breakdown**:
   - `GET /analytics/categories`
   - Click "Execute"
   - See spending by category

7. **Export Transactions**:
   - `GET /transactions/export`
   - Add filters if needed
   - Click "Execute"
   - Downloads CSV file

## Understanding the UI

### Endpoint Colors
- 🟢 **GET** (Green) - Retrieve data
- 🟡 **POST** (Yellow) - Create/trigger actions
- 🔵 **PUT** (Blue) - Update data
- 🔴 **DELETE** (Red) - Remove data

### Request Parameters
- **Path Parameters**: Part of the URL (e.g., `/transactions/{id}`)
- **Query Parameters**: URL parameters (e.g., `?skip=0&limit=10`)
- **Request Body**: JSON data sent with POST/PUT requests
- **Headers**: HTTP headers (usually auto-managed)

### Response Information
- **Status Code**: HTTP status (200 = success, 401 = unauthorized, etc.)
- **Response Body**: JSON data returned by the endpoint
- **Response Headers**: HTTP headers from server
- **Curl Command**: Copy to use in terminal

## Common Testing Scenarios

### Scenario 1: First Time Setup
```
1. GET /debug/db          → Verify database is connected
2. GET /auth/google       → Login (in browser)
3. GET /auth/me           → Confirm authentication
4. POST /sync/manual      → Fetch emails
5. GET /transactions      → View parsed transactions
```

### Scenario 2: Daily Usage
```
1. GET /auth/me           → Check if still logged in
2. POST /sync/manual      → Sync new emails
3. GET /analytics/summary → View spending overview
4. GET /transactions      → Browse recent expenses
```

### Scenario 3: Data Analysis
```
1. GET /analytics/monthly?months=12  → Year-long trends
2. GET /analytics/categories         → Category breakdown
3. GET /transactions/export          → Download CSV for Excel
```

## Troubleshooting

### "401 Unauthorized" Errors
- You need to authenticate first
- Go to http://localhost:8000/auth/google in a new tab
- Complete OAuth flow
- Return to Swagger UI

### "500 Internal Server Error"
- Check server logs in terminal
- Verify database is running: `GET /debug/db`
- Check .env file has correct credentials

### "422 Unprocessable Entity"
- Invalid request parameters
- Check the "Schema" section for required fields
- Ensure data types match (string, number, etc.)

### Cookies Not Working
- Swagger UI shares cookies with your browser session
- If issues persist, use Postman or curl for testing
- Or test directly in browser for GET endpoints

## Advanced Features

### Schemas
Click on "Schemas" at the bottom to see:
- Request/response data models
- Field types and validations
- Example values

### Try Different Filters
Many endpoints support filtering:
```
GET /transactions?transaction_type=debit&min_amount=100&max_amount=1000
GET /analytics/monthly?months=3
GET /sync/history?limit=10
```

### Download OpenAPI Spec
- Click "Download" button in Swagger UI
- Get OpenAPI JSON specification
- Import into Postman, Insomnia, or other tools

## Tips for Effective Testing

1. **Start Simple**: Test health endpoints first
2. **Check Responses**: Verify data structure matches expectations
3. **Use Filters**: Test query parameters to narrow results
4. **Check Edge Cases**: Try invalid inputs, empty results, etc.
5. **Monitor Logs**: Watch terminal for server-side errors
6. **Test Sequentially**: Some endpoints depend on others (auth → sync → transactions)

## Alternative Testing Tools

If Swagger UI doesn't meet your needs:

### Postman
- Import OpenAPI spec from http://localhost:8000/openapi.json
- Better cookie/session management
- Can save request collections

### curl (Command Line)
```bash
# Health check
curl http://localhost:8000/

# Database status
curl http://localhost:8000/debug/db

# With authentication (after OAuth)
curl http://localhost:8000/auth/me -b "session_token=YOUR_TOKEN"
```

### HTTPie (Command Line)
```bash
# Install: pip install httpie
http GET http://localhost:8000/
http GET http://localhost:8000/debug/db
```

## Next Steps

1. ✅ Verify server is running
2. ✅ Test health endpoints
3. ✅ Complete OAuth authentication
4. ✅ Trigger manual sync
5. ✅ Explore your transactions
6. ✅ View analytics
7. ✅ Export data

Happy testing! 🚀
