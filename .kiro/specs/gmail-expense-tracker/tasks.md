# Implementation Plan: Gmail AI Expense Tracker

## Overview

This implementation plan breaks down the Gmail AI Expense Tracker into discrete, incremental coding tasks. Each task builds on previous work, with property-based tests integrated throughout to validate correctness early. The plan follows the architecture defined in the design document and ensures all 12 requirements and 31 correctness properties are implemented.

## Tasks

- [ ] 1. Project Setup and Database Foundation
  - [x] 1.1 Initialize backend project structure
    - Create backend/ directory with app/ subdirectories: models/, schemas/, routes/, services/, auth/, scheduler/
    - Set up Python virtual environment and install dependencies: fastapi, sqlalchemy[asyncio], asyncpg, pydantic, python-jose, cryptography, google-auth, google-api-python-client, apscheduler, structlog, tenacity, alembic, pytest, hypothesis, pytest-asyncio, python-dateutil
    - Create .env.example with all required environment variables
    - Create main.py with FastAPI app initialization
    - _Requirements: 10.3_

  - [x] 1.2 Configure Neon PostgreSQL connection
    - Implement app/database.py with async engine configuration
    - Set up connection pooling (pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=3600)
    - Configure SSL mode for Neon compatibility
    - Implement async session factory and get_db() dependency
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.3 Create database models
    - Implement app/models/user.py with User model (UUID id, email unique, name, google_id unique, refresh_token_encrypted, created_at)
    - Implement app/models/transaction.py with Transaction model (UUID id, user_id FK, amount Numeric, currency, transaction_type enum, merchant, transaction_date, bank_name, gmail_message_id unique, created_at)
    - Implement app/models/sync_log.py with SyncLog model (UUID id, user_id FK, status, emails_processed, errors, created_at)
    - Add indexes on user_id columns
    - _Requirements: 1.4, 1.5, 1.6, 1.7_

  - [ ] 1.3.1 Fix datetime handling in database models
    - Update all models to use DateTime(timezone=True) for timezone-aware columns
    - Update default values to use lambda: datetime.now(timezone.utc) instead of datetime.utcnow
    - Ensure transaction_date, created_at columns are timezone-aware
    - _Requirements: 13.1, 13.2, 13.5_

  - [x] 1.4 Write property test for gmail_message_id uniqueness
    - **Property 1: Gmail Message ID Uniqueness (Idempotency)**
    - **Validates: Requirements 1.8, 3.3**

  - [x] 1.5 Set up Alembic migrations
    - Initialize Alembic with alembic init alembic
    - Configure alembic.ini for async PostgreSQL
    - Create initial migration for all three tables
    - Test upgrade and downgrade migrations
    - _Requirements: 8.1, 8.2_

  - [ ] 1.5.1 Create migration for timezone-aware datetime columns
    - Create new Alembic migration to update DateTime columns to DateTime(timezone=True)
    - Update existing data to ensure all timestamps are in UTC
    - Test migration upgrade and downgrade
    - _Requirements: 13.1, 13.2_

  - [ ] 1.6 Write property test for migration reversibility
    - **Property 25: Migration Reversibility**
    - **Validates: Requirements 8.4**

- [x] 2. Checkpoint - Database foundation complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Authentication and Security Module
  - [x] 3.1 Implement encryption utilities
    - Create app/auth/encryption.py with Fernet-based encryption
    - Implement encrypt_refresh_token() and decrypt_refresh_token()
    - Load encryption key from environment variable
    - _Requirements: 2.3, 7.1_

  - [x] 3.2 Write property test for refresh token encryption
    - **Property 3: Refresh Token Encryption**
    - **Validates: Requirements 2.3, 7.1**

  - [x] 3.3 Implement JWT handling
    - Create app/auth/jwt_handler.py
    - Implement create_session_token(user_id, email) returning JWT
    - Implement verify_session_token(token) with validation
    - Configure JWT secret, algorithm (HS256), and expiration (7 days)
    - _Requirements: 2.4_

  - [ ] 3.3.1 Fix datetime usage in JWT handler
    - Replace datetime.utcnow() with datetime.now(timezone.utc)
    - Ensure all JWT timestamps are timezone-aware
    - _Requirements: 13.1, 13.5_

  - [x] 3.4 Write property test for session token generation
    - **Property 4: Session Token Generation**
    - **Validates: Requirements 2.4, 2.5**

  - [x] 3.5 Write property test for JWT validation
    - **Property 20: JWT Validation on Protected Endpoints**
    - **Validates: Requirements 7.4**

  - [x] 3.6 Implement Google OAuth flow
    - Create app/auth/oauth.py
    - Implement initiate_oauth_flow() generating authorization URL with scopes: gmail.readonly, openid, email, profile
    - Implement handle_oauth_callback(code) exchanging code for tokens
    - Implement refresh_access_token(refresh_token) for token refresh
    - Add retry logic with tenacity for token refresh
    - _Requirements: 2.1, 2.2, 2.6_

  - [x] 3.7 Write property test for OAuth token exchange
    - **Property 2: OAuth Token Exchange**
    - **Validates: Requirements 2.2**

  - [x] 3.8 Write property test for token refresh
    - **Property 5: Token Refresh on Expiration**
    - **Validates: Requirements 2.6**

  - [x] 3.9 Write property test for token refresh failure handling
    - **Property 6: Token Refresh Failure Handling**
    - **Validates: Requirements 2.7**

  - [x] 3.10 Create authentication middleware
    - Implement get_current_user() dependency that validates JWT from cookie
    - Return 401 Unauthorized for invalid/missing tokens
    - _Requirements: 7.4_

  - [x] 3.11 Implement Pydantic schemas for authentication
    - Create app/schemas/user.py with UserBase, UserResponse
    - Create app/schemas/auth.py with TokenResponse, LoginResponse
    - _Requirements: 7.6_


- [ ] 4. Authentication API Routes
  - [x] 4.1 Implement authentication routes
    - Create app/routes/auth.py
    - Implement GET /auth/google endpoint initiating OAuth flow
    - Implement GET /auth/callback endpoint handling OAuth callback, encrypting refresh token, storing user, generating JWT, setting HTTPOnly secure cookie
    - Implement GET /auth/me endpoint returning current user info
    - Implement POST /auth/logout endpoint clearing session cookie
    - _Requirements: 2.5, 2.7, 7.9, 9.1, 9.2, 9.3_

  - [x] 4.2 Write property test for HTTPOnly cookie setting
    - **Property 4: Session Token Generation** (cookie attributes)
    - **Validates: Requirements 2.5**

  - [x] 4.3 Write property test for logout session clearing
    - **Property 24: Logout Session Clearing**
    - **Validates: Requirements 7.9**

  - [x] 4.4 Write property test for client secret protection
    - **Property 19: Client Secret Protection**
    - **Validates: Requirements 7.2**

  - [x] 4.5 Write unit tests for authentication routes
    - Test OAuth URL generation contains correct scopes
    - Test callback with valid code creates user and sets cookie
    - Test /auth/me with valid token returns user
    - Test /auth/me with invalid token returns 401
    - Test logout clears cookie
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 7.9_

- [x] 5. Checkpoint - Authentication complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Gmail Integration Service
  - [x] 6.1 Implement Gmail API service
    - Create app/services/gmail_service.py
    - Implement fetch_transaction_emails(access_token, last_sync_time) using Gmail API
    - Use search query: ("INR" OR "Rs" OR "debited" OR "credited")
    - Implement get_email_content(access_token, message_id) fetching full email
    - Add retry logic with exponential backoff using tenacity
    - Add structured logging for all API calls
    - _Requirements: 3.1, 3.4, 11.2_

  - [x] 6.2 Write property test for email content completeness
    - **Property 8: Email Content Completeness**
    - **Validates: Requirements 3.4**

  - [x] 6.3 Write unit tests for Gmail service
    - Mock Gmail API responses
    - Test search query is correctly formatted
    - Test email fetching returns subject and body
    - Test retry logic on API failures
    - Test error handling for rate limits
    - _Requirements: 3.1, 3.4_

- [ ] 7. Email Parser Module
  - [x] 7.1 Implement email parser
    - Create app/services/email_parser.py
    - Define ParsedTransaction Pydantic model
    - Implement parse_email(subject, body) returning ParsedTransaction or None
    - Implement extract_amount(text) with regex patterns for Indian formats
    - Implement extract_transaction_type(text) identifying debit/credit
    - Implement extract_merchant(text) with regex patterns
    - Implement extract_date(text) with multiple date format patterns
    - Implement extract_bank(text) identifying bank from sender/content
    - Add structured logging for parsing attempts
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.9, 11.3_

  - [ ] 7.1.1 Fix date handling issues in email parser
    - Update extract_date() to return None instead of datetime.utcnow() when no date found
    - Update extract_date() to return timezone-aware datetime objects in UTC
    - Update parse_email() to properly handle None date (return None for entire parse)
    - Add pytz or use datetime.timezone for timezone handling
    - _Requirements: 4.10, 4.11, 13.1, 13.4, 13.5_

  - [x] 7.2 Write property test for parser completeness
    - **Property 10: Email Parser Completeness**
    - **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**

  - [x] 7.3 Write property test for parser error handling
    - **Property 11: Parser Error Handling**
    - **Validates: Requirements 4.9**

  - [ ] 7.3.1 Write property test for date extraction returning None
    - **Property 32: Date Extraction Returns None for Missing Dates**
    - **Validates: Requirements 4.10, 13.4**

  - [ ] 7.3.2 Write property test for timezone-aware datetime consistency
    - **Property 33: Timezone-Aware Datetime Consistency**
    - **Validates: Requirements 13.1, 13.2, 13.5**

  - [x] 7.4 Write unit tests for email parser
    - Test parsing sample emails from HDFC, ICICI, SBI, Axis Bank
    - Test edge cases: missing merchant, malformed dates, special characters
    - Test debit vs credit identification
    - Test amount extraction with various formats (Rs, INR, commas)
    - Test parser returns None for unparseable emails
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6, 4.9_

  - [ ] 7.4.1 Add unit tests for date handling edge cases
    - Test extract_date returns None for emails without dates
    - Test extract_date returns timezone-aware UTC datetime
    - Test parse_email returns None when date is missing
    - _Requirements: 4.10, 4.11, 13.1, 13.4, 13.5_

- [ ] 8. Transaction Management
  - [x] 8.1 Implement transaction schemas
    - Create app/schemas/transaction.py
    - Define TransactionBase, TransactionResponse, TransactionListResponse
    - Add validation for amount, currency, transaction_type
    - _Requirements: 7.6_

  - [x] 8.2 Implement transaction database operations
    - Create app/services/transaction_service.py
    - Implement create_transaction(db, user_id, parsed_transaction, message_id)
    - Implement get_transactions(db, user_id, filters, pagination)
    - Implement get_processed_message_ids(db, user_id) for duplicate checking
    - Handle unique constraint violations gracefully
    - _Requirements: 3.2, 3.3, 3.5_

  - [x] 8.3 Write property test for duplicate email filtering
    - **Property 7: Duplicate Email Filtering**
    - **Validates: Requirements 3.2, 3.3**

  - [x] 8.4 Write property test for message ID persistence
    - **Property 9: Message ID Persistence**
    - **Validates: Requirements 3.5**

  - [x] 8.3 Implement transaction routes
    - Create app/routes/transactions.py
    - Implement GET /transactions with pagination (max 100), filtering (date range, type, merchant), sorting
    - Implement GET /transactions/export for CSV export
    - Add authentication middleware to all routes
    - _Requirements: 6.8, 6.9, 9.4, 12.3_

  - [ ] 8.6 Write property test for transaction pagination
    - **Property 17: Transaction Pagination**
    - **Validates: Requirements 6.8, 12.3**

  - [ ] 8.7 Write property test for transaction filtering
    - **Property 18: Transaction Filtering**
    - **Validates: Requirements 6.9**

  - [ ] 8.8 Write property test for CSV export format
    - **Property 16: CSV Export Format**
    - **Validates: Requirements 6.6**

- [x] 9. Checkpoint - Core transaction handling complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9.1 Checkpoint - Date and timezone fixes
  - Complete tasks 1.3.1, 1.5.1, 3.3.1, 7.1.1, 7.3.1, 7.3.2, 7.4.1, 10.2.1, 10.4.1
  - Verify all datetime objects are timezone-aware (UTC)
  - Verify extract_date returns None for missing dates
  - Verify analytics uses proper month calculations
  - Run all property tests for date handling
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Analytics and Dashboard APIs
  - [x] 10.1 Implement analytics schemas
    - Create app/schemas/analytics.py
    - Define SummaryResponse, MonthlyDataPoint, CategoryDataPoint
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 10.2 Implement analytics service
    - Create app/services/analytics_service.py
    - Implement get_summary(db, user_id) calculating total spent, received, transaction count
    - Implement get_monthly_data(db, user_id, months) aggregating by month
    - Implement get_category_breakdown(db, user_id) grouping by merchant
    - Use async SQLAlchemy queries with aggregations
    - _Requirements: 6.2, 6.3, 6.4_

  - [ ] 10.2.1 Fix date calculations in analytics service
    - Replace datetime.now() with datetime.now(timezone.utc) for consistency
    - Replace approximate month calculation (months * 30) with python-dateutil relativedelta
    - Import: from dateutil.relativedelta import relativedelta
    - Update: start_date = datetime.now(timezone.utc) - relativedelta(months=months)
    - Ensure all datetime comparisons use timezone-aware objects
    - _Requirements: 13.1, 13.3, 13.5_

  - [x] 10.3 Implement analytics routes
    - Create app/routes/analytics.py
    - Implement GET /analytics/summary
    - Implement GET /analytics/monthly with months parameter
    - Implement GET /analytics/categories
    - Add authentication middleware
    - _Requirements: 9.6, 9.7_

  - [ ] 10.4 Write unit tests for analytics
    - Test summary calculation with sample transactions
    - Test monthly aggregation
    - Test category breakdown
    - Test with empty transaction list
    - _Requirements: 6.2, 6.3, 6.4_

  - [ ] 10.4.1 Add unit tests for date range calculations
    - Test monthly data with proper month boundaries (not 30-day approximations)
    - Test date filtering with timezone-aware datetimes
    - Test edge cases: leap years, month boundaries
    - _Requirements: 13.1, 13.3, 13.5_

- [ ] 11. Automatic Sync Scheduler
  - [x] 11.1 Implement sync service
    - Create app/scheduler/sync_job.py
    - Implement sync_all_users() fetching all users and processing each
    - Implement sync_user_emails(user, session) handling single user sync
    - Decrypt refresh token, refresh access token
    - Fetch new emails from Gmail
    - Filter out processed message IDs
    - Parse emails and insert transactions
    - Create sync_log entry with status and count
    - Handle errors per user without stopping batch
    - Ensure short-lived database sessions
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.10_

  - [ ] 11.2 Write property test for sync user processing
    - **Property 12: Sync User Processing**
    - **Validates: Requirements 5.2**

  - [ ] 11.3 Write property test for sync transaction insertion
    - **Property 13: Sync Transaction Insertion**
    - **Validates: Requirements 5.6**

  - [ ] 11.4 Write property test for sync logging
    - **Property 14: Sync Logging**
    - **Validates: Requirements 5.7**

  - [ ] 11.5 Write property test for sync error isolation
    - **Property 15: Sync Error Isolation**
    - **Validates: Requirements 5.10**

  - [x] 11.6 Implement scheduler initialization
    - Create start_scheduler() function in sync_job.py
    - Configure APScheduler with AsyncIOScheduler
    - Add job with 15-minute interval
    - Call start_scheduler() in main.py on app startup
    - _Requirements: 5.1_

  - [x] 11.7 Implement sync routes
    - Create app/routes/sync.py
    - Implement POST /sync/manual triggering immediate sync for current user
    - Implement GET /sync/history returning sync logs
    - Add authentication middleware
    - _Requirements: 9.5, 9.8_

  - [ ] 11.8 Write unit tests for sync service
    - Mock Gmail API and database
    - Test sync processes all users
    - Test sync skips already processed emails
    - Test sync creates log entries
    - Test sync continues after user failure
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.10_

- [ ] 12. Checkpoint - Backend sync system complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Security and Error Handling
  - [ ] 13.1 Implement rate limiting middleware
    - Install slowapi package
    - Create rate limiting middleware for auth and API endpoints
    - Configure limits: 5 requests/minute for auth, 100 requests/minute for API
    - _Requirements: 7.5_

  - [ ] 13.2 Write property test for rate limiting
    - **Property 21: Rate Limiting Enforcement**
    - **Validates: Requirements 7.5**

  - [ ] 13.3 Implement input validation
    - Ensure all route handlers use Pydantic schemas
    - Add custom validators for email, dates, amounts
    - Return 422 with validation details on errors
    - _Requirements: 7.6_

  - [ ] 13.4 Write property test for input validation
    - **Property 22: Input Validation**
    - **Validates: Requirements 7.6**

  - [ ] 13.5 Implement CORS configuration
    - Configure CORS middleware in main.py
    - Allow only frontend origin from environment variable
    - Enable credentials (withCredentials)
    - _Requirements: 2.8, 7.8_

  - [ ] 13.6 Write property test for CORS validation
    - **Property 23: CORS Origin Validation**
    - **Validates: Requirements 7.8**

  - [ ] 13.7 Implement error handling middleware
    - Create global exception handler
    - Return consistent error format with correlation_id
    - Map exceptions to appropriate HTTP status codes
    - Ensure user-friendly error messages (no stack traces)
    - _Requirements: 9.10, 11.5_

  - [ ] 13.8 Write property test for error response consistency
    - **Property 26: Error Response Consistency**
    - **Validates: Requirements 9.10**

  - [ ] 13.9 Write property test for error message user-friendliness
    - **Property 29: Error Message User-Friendliness**
    - **Validates: Requirements 11.5**

  - [ ] 13.10 Implement request correlation ID middleware
    - Generate UUID for each request
    - Add to request context
    - Include in all log entries
    - Include in error responses
    - _Requirements: 11.7_

  - [ ] 13.11 Write property test for request correlation
    - **Property 30: Request Correlation**
    - **Validates: Requirements 11.7**

  - [ ] 13.12 Implement request timeout
    - Configure FastAPI timeout middleware
    - Set timeout to 30 seconds
    - Return 504 Gateway Timeout on exceeded requests
    - _Requirements: 12.7_

  - [ ] 13.13 Write property test for request timeout
    - **Property 31: Request Timeout Enforcement**
    - **Validates: Requirements 12.7**

- [ ] 14. Logging and Monitoring
  - [ ] 14.1 Configure structured logging
    - Set up structlog in main.py
    - Configure log format, processors, and output
    - Add logging to all authentication attempts
    - Add logging to all Gmail API calls
    - Add logging to all parsing attempts
    - Add logging to all database errors
    - Add logging to sync job events
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.8_

  - [ ] 14.2 Write property test for authentication logging
    - **Property 28: Authentication Logging**
    - **Validates: Requirements 11.1**

  - [ ] 14.3 Write unit tests for logging
    - Test log entries are created for key events
    - Test correlation IDs are included
    - Test sensitive data is not logged
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.7, 11.8_

- [ ] 15. Environment Configuration and Startup
  - [ ] 15.1 Implement environment variable validation
    - Create app/config.py with Settings class using Pydantic BaseSettings
    - Define all required environment variables: DATABASE_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, JWT_SECRET, ENCRYPTION_KEY, FRONTEND_URL
    - Validate on app startup, fail with clear error if missing
    - _Requirements: 10.10_

  - [ ] 15.2 Write property test for environment validation
    - **Property 27: Environment Variable Validation**
    - **Validates: Requirements 10.10**

  - [ ] 15.3 Complete main.py application setup
    - Import all routers and register with app
    - Add CORS middleware
    - Add rate limiting middleware
    - Add error handling middleware
    - Add correlation ID middleware
    - Add timeout middleware
    - Start scheduler on startup
    - Add OpenAPI documentation configuration
    - _Requirements: 2.8, 7.5, 9.9, 11.7, 12.7_

  - [ ] 15.4 Write unit tests for application startup
    - Test app starts successfully with valid config
    - Test app fails with clear error on missing env vars
    - Test all routes are registered
    - Test OpenAPI docs are available at /docs
    - _Requirements: 10.10, 9.9_

- [ ] 16. Checkpoint - Backend complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 17. Frontend Project Setup
  - [x] 17.1 Initialize frontend project
    - Create frontend/ directory
    - Initialize Vite + React + TypeScript project
    - Install dependencies: react, react-dom, react-router-dom, axios, recharts, tailwindcss, date-fns
    - Configure Tailwind CSS
    - Set up TypeScript configuration
    - Create src/ directory structure: pages/, components/, services/, hooks/, context/, types/
    - _Requirements: 6.1_

  - [x] 17.2 Configure Axios client
    - Create src/services/api.ts
    - Configure axios instance with baseURL from environment
    - Enable withCredentials for cookie handling
    - Add request/response interceptors for error handling
    - _Requirements: 2.8_

  - [x] 17.3 Define TypeScript types
    - Create src/types/index.ts
    - Define User, Transaction, Summary, MonthlyData, CategoryData types
    - Define API response types
    - _Requirements: 6.2, 6.3, 6.4, 6.8_

- [ ] 18. Authentication Context and Protected Routes
  - [x] 18.1 Implement authentication context
    - Create src/context/AuthContext.tsx
    - Implement AuthProvider with user state, loading state
    - Implement login() redirecting to backend OAuth
    - Implement logout() calling backend and clearing state
    - Implement checkAuth() calling /auth/me on mount
    - _Requirements: 2.1, 2.7, 7.9_

  - [x] 18.2 Implement protected route component
    - Create src/components/ProtectedRoute.tsx
    - Check authentication status
    - Redirect to login if not authenticated
    - Show loading state while checking
    - _Requirements: 7.4_

  - [x] 18.3 Set up React Router
    - Create src/App.tsx with router configuration
    - Define routes: /, /dashboard, /transactions, /settings
    - Wrap protected routes with ProtectedRoute
    - _Requirements: 6.1_

- [ ] 19. Login Page
  - [x] 19.1 Implement login page
    - Create src/pages/Login.tsx
    - Display "Login with Google" button
    - Button redirects to backend /auth/google
    - Add styling with Tailwind CSS
    - _Requirements: 2.1, 6.1_

  - [ ] 19.2 Write unit tests for login page
    - Test login button renders
    - Test button click redirects to OAuth
    - _Requirements: 2.1_

- [ ] 20. Dashboard Page
  - [x] 20.1 Implement dashboard data fetching
    - Create src/hooks/useDashboardData.ts
    - Fetch summary, monthly data, and categories on mount
    - Handle loading and error states
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 20.2 Implement summary cards component
    - Create src/components/SummaryCards.tsx
    - Display total spent, total received, transaction count
    - Display last sync time
    - Add responsive grid layout
    - _Requirements: 6.2_

  - [x] 20.3 Implement monthly chart component
    - Create src/components/MonthlyChart.tsx
    - Use Recharts LineChart or BarChart
    - Display monthly spending trends
    - Add tooltips and axis labels
    - _Requirements: 6.3_

  - [x] 20.4 Implement category breakdown component
    - Create src/components/CategoryBreakdown.tsx
    - Use Recharts PieChart
    - Display spending by merchant
    - Add legend and percentages
    - _Requirements: 6.4_

  - [x] 20.5 Implement sync button component
    - Create src/components/SyncButton.tsx
    - Call POST /sync/manual on click
    - Show loading state during sync
    - Refresh dashboard data after sync
    - _Requirements: 6.5_

  - [x] 20.6 Implement CSV export button
    - Create src/components/ExportButton.tsx
    - Call GET /transactions/export
    - Trigger browser download of CSV file
    - _Requirements: 6.6_

  - [x] 20.7 Implement dark mode toggle
    - Create src/hooks/useDarkMode.ts
    - Store preference in localStorage
    - Toggle Tailwind dark mode classes
    - Add toggle button to dashboard
    - _Requirements: 6.7_

  - [x] 20.8 Assemble dashboard page
    - Create src/pages/Dashboard.tsx
    - Compose all dashboard components
    - Add loading and error states
    - Add responsive layout
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ] 20.9 Write unit tests for dashboard components
    - Test summary cards render with data
    - Test charts render with data
    - Test sync button triggers API call
    - Test export button downloads CSV
    - Test dark mode toggle works
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [ ] 21. Transactions Page
  - [x] 21.1 Implement transaction list component
    - Create src/components/TransactionList.tsx
    - Display transactions in table format
    - Show amount, type, merchant, date, bank
    - Add responsive design for mobile
    - _Requirements: 6.8_

  - [x] 21.2 Implement filter bar component
    - Create src/components/FilterBar.tsx
    - Add date range picker
    - Add transaction type dropdown (all, debit, credit)
    - Add merchant search input
    - Update URL query params on filter change
    - _Requirements: 6.9_

  - [x] 21.3 Implement pagination component
    - Create src/components/Pagination.tsx
    - Show page numbers and navigation buttons
    - Update URL query params on page change
    - _Requirements: 6.8_

  - [x] 21.4 Assemble transactions page
    - Create src/pages/Transactions.tsx
    - Fetch transactions with filters and pagination
    - Compose filter bar, transaction list, and pagination
    - Handle loading and error states
    - _Requirements: 6.1, 6.8, 6.9_

  - [ ] 21.5 Write unit tests for transactions page
    - Test transaction list renders
    - Test filters update query params
    - Test pagination works
    - _Requirements: 6.8, 6.9_

- [ ] 22. Settings Page
  - [x] 22.1 Implement settings page
    - Create src/pages/Settings.tsx
    - Display user account information
    - Display sync history table
    - Add dark mode toggle
    - Add logout button
    - _Requirements: 6.1, 6.10_

  - [ ] 22.2 Write unit tests for settings page
    - Test user info displays
    - Test sync history renders
    - Test logout button works
    - _Requirements: 6.10_

- [ ] 23. Checkpoint - Frontend complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 24. Docker and Deployment Configuration
  - [ ] 24.1 Create backend Dockerfile
    - Create backend/Dockerfile
    - Use Python 3.11 slim base image
    - Install dependencies from requirements.txt
    - Set up non-root user
    - Expose port 8000
    - Set CMD to run uvicorn
    - _Requirements: 10.1_

  - [ ] 24.2 Create docker-compose.yml
    - Create docker-compose.yml in root
    - Define backend service with environment variables
    - Configure for local development (no database service, use external Neon)
    - Add volume mounts for development
    - _Requirements: 10.2_

  - [ ] 24.3 Create frontend Dockerfile
    - Create frontend/Dockerfile
    - Use Node 18 base image
    - Install dependencies and build
    - Use nginx to serve static files
    - Expose port 80
    - _Requirements: 10.1_

  - [ ] 24.4 Create deployment documentation
    - Create DEPLOYMENT.md in root
    - Document Neon database setup steps
    - Document Gmail API enablement steps
    - Document OAuth credential configuration
    - Document backend deployment to Render/Railway
    - Document frontend deployment to Vercel/Netlify
    - Document environment variable configuration
    - _Requirements: 10.6, 10.7, 10.8, 10.9_

- [ ] 25. Documentation and README
  - [ ] 25.1 Create comprehensive README
    - Create README.md in root
    - Add project overview and features
    - Add architecture diagram
    - Add tech stack list
    - Add setup instructions for local development
    - Add testing instructions
    - Add deployment instructions
    - Add API documentation link
    - Add screenshots (placeholders)
    - _Requirements: 10.6_

  - [ ] 25.2 Create API documentation
    - Ensure OpenAPI/Swagger docs are complete at /docs
    - Add descriptions to all endpoints
    - Add request/response examples
    - Document authentication requirements
    - _Requirements: 9.9_

  - [ ] 25.3 Create requirements.txt
    - Generate requirements.txt with all Python dependencies
    - Pin versions for reproducibility
    - _Requirements: 10.3_

  - [ ] 25.4 Create frontend .env.example
    - Create frontend/.env.example
    - Document VITE_API_URL variable
    - _Requirements: 10.3_

- [ ] 26. Final Integration and Testing
  - [ ] 26.1 Run full test suite
    - Run all backend unit tests
    - Run all backend property-based tests
    - Run all frontend unit tests
    - Verify minimum 80% backend coverage
    - Verify minimum 70% frontend coverage
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ] 26.2 Manual integration testing
    - Test complete OAuth flow end-to-end
    - Test manual sync from dashboard
    - Test transaction filtering and pagination
    - Test CSV export
    - Test dark mode
    - Test error handling (invalid tokens, API failures)
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [ ] 26.3 Performance testing
    - Test with 1000+ transactions
    - Verify pagination performance
    - Verify dashboard load time
    - Verify sync job completes within reasonable time
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ] 27. Final checkpoint - Project complete
  - Ensure all tests pass, all documentation is complete, and the application is ready for deployment.

## Notes

- Tasks marked with `*` are optional property-based and unit test tasks that can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Property-based tests use Hypothesis with minimum 100 iterations
- All async operations use async/await patterns
- Database sessions are short-lived and properly managed
- Security is enforced at every layer (encryption, JWT, CORS, rate limiting, input validation)
- The implementation follows the exact architecture defined in the design document
