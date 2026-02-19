# Requirements Document

## Introduction

The Gmail AI Expense Tracker is a production-ready web application that automatically tracks financial transactions by analyzing Gmail emails. The system authenticates users via Google OAuth 2.0, fetches transaction-related emails from Gmail, parses transaction details using pattern matching, stores structured data in Neon serverless PostgreSQL, and provides a comprehensive financial analytics dashboard with automatic periodic synchronization.

## Glossary

- **System**: The Gmail AI Expense Tracker application (backend + frontend)
- **Backend**: FastAPI server handling authentication, Gmail API integration, and data processing
- **Frontend**: React-based web interface for user interaction and data visualization
- **Database**: Neon serverless PostgreSQL instance
- **Gmail_API**: Google's Gmail API service for email access
- **OAuth_Service**: Google OAuth 2.0 authentication service
- **Email_Parser**: Module responsible for extracting transaction data from email content
- **Scheduler**: APScheduler service for periodic email synchronization
- **User**: End user of the expense tracker application
- **Transaction**: A financial transaction record (debit or credit)
- **Sync_Process**: Automated process that fetches and processes new Gmail emails
- **Session_Token**: Internal JWT token stored in HTTPOnly cookie for user sessions
- **Refresh_Token**: Google OAuth refresh token for obtaining new access tokens
- **Message_ID**: Unique Gmail message identifier to prevent duplicate processing

## Requirements

### Requirement 1: Database Infrastructure

**User Story:** As a system architect, I want a robust serverless PostgreSQL database infrastructure, so that the application can scale efficiently and handle concurrent operations reliably.

#### Acceptance Criteria

1. THE Database SHALL connect to Neon PostgreSQL using the DATABASE_URL environment variable
2. THE Database SHALL enforce SSL mode as required with connection pooling enabled
3. THE Database SHALL use SQLAlchemy async engine with proper session management
4. THE Database SHALL include a users table with columns: id (UUID primary key), email (unique), name, google_id (unique), refresh_token_encrypted, created_at (timestamp)
5. THE Database SHALL include a transactions table with columns: id (UUID primary key), user_id (foreign key), amount (Numeric), currency, transaction_type (enum: debit/credit), merchant, transaction_date, bank_name, gmail_message_id (unique), created_at (timestamp)
6. THE Database SHALL include a sync_logs table with columns: id (UUID primary key), user_id (foreign key), status, emails_processed (integer), created_at (timestamp)
7. THE Database SHALL create indexes on user_id columns in transactions and sync_logs tables
8. THE Database SHALL enforce unique constraint on gmail_message_id in transactions table

### Requirement 2: Google OAuth Authentication

**User Story:** As a user, I want to securely authenticate using my Google account, so that the application can access my Gmail emails with proper authorization.

#### Acceptance Criteria

1. WHEN a user initiates login, THE OAuth_Service SHALL request scopes: gmail.readonly, openid, email, profile
2. WHEN the Frontend redirects to the Backend with authorization code, THE Backend SHALL exchange the code for access and refresh tokens
3. WHEN tokens are received, THE Backend SHALL encrypt the refresh token before storing it in the Database
4. WHEN authentication succeeds, THE Backend SHALL generate an internal JWT session token
5. THE Backend SHALL store the session token in an HTTPOnly secure cookie
6. WHEN an access token expires, THE Backend SHALL use the refresh token to obtain a new access token
7. IF token refresh fails, THEN THE Backend SHALL return an authentication error and clear the session
8. THE Backend SHALL implement proper CORS configuration for Frontend-Backend communication

### Requirement 3: Gmail Email Fetching

**User Story:** As a user, I want the system to automatically fetch transaction-related emails from my Gmail, so that my expenses are tracked without manual entry.

#### Acceptance Criteria

1. WHEN fetching emails, THE Gmail_API SHALL search using the query: ("INR" OR "Rs" OR "debited" OR "credited")
2. WHEN processing emails, THE System SHALL check gmail_message_id against the Database to identify already processed messages
3. THE System SHALL skip emails with gmail_message_id that already exist in the transactions table
4. WHEN new emails are found, THE System SHALL fetch the full email content including subject and body
5. THE System SHALL store the gmail_message_id in the Database after successful processing

### Requirement 4: Email Parsing and Transaction Extraction

**User Story:** As a developer, I want a robust email parser that extracts transaction details from various bank email formats, so that transaction data is accurately captured.

#### Acceptance Criteria

1. THE Email_Parser SHALL be implemented in app/services/email_parser.py
2. WHEN parsing an email, THE Email_Parser SHALL extract the transaction amount using regex patterns
3. WHEN parsing an email, THE Email_Parser SHALL identify whether the transaction is a debit or credit
4. WHEN parsing an email, THE Email_Parser SHALL extract the merchant name
5. WHEN parsing an email, THE Email_Parser SHALL extract the transaction date
6. WHEN parsing an email, THE Email_Parser SHALL identify the bank name
7. THE Email_Parser SHALL support Indian bank email formats
8. THE Email_Parser SHALL be designed with extensibility for future ML-based improvements
9. IF parsing fails to extract required fields, THEN THE Email_Parser SHALL return an error indicator
10. THE Email_Parser SHALL return None for transaction_date if no valid date is found (no fallback to current date)
11. THE Email_Parser SHALL use timezone-aware datetime objects in UTC for all date operations

### Requirement 5: Automatic Synchronization

**User Story:** As a user, I want the system to automatically sync my Gmail emails periodically, so that my expense tracker stays up-to-date without manual intervention.

#### Acceptance Criteria

1. THE Scheduler SHALL use APScheduler to run synchronization every 15 minutes
2. WHEN sync runs, THE Scheduler SHALL fetch all active users from the Database
3. FOR each active user, THE Scheduler SHALL refresh the access token using the stored refresh token
4. FOR each active user, THE Scheduler SHALL fetch new emails from Gmail_API
5. FOR each new email, THE Scheduler SHALL invoke the Email_Parser to extract transaction data
6. WHEN transaction data is extracted, THE Scheduler SHALL insert the transaction record into the Database
7. WHEN sync completes, THE Scheduler SHALL log the sync results in the sync_logs table
8. THE Scheduler SHALL ensure database sessions are short-lived and properly closed
9. THE Scheduler SHALL handle Neon idle timeout gracefully without connection leakage
10. IF sync fails for a user, THEN THE Scheduler SHALL log the error and continue processing other users

### Requirement 6: Frontend Dashboard and User Interface

**User Story:** As a user, I want an intuitive dashboard that displays my financial analytics and allows me to manage my transactions, so that I can understand my spending patterns.

#### Acceptance Criteria

1. THE Frontend SHALL include pages: Login, Dashboard, Transactions, Settings
2. THE Dashboard SHALL display total amount spent
3. THE Dashboard SHALL display a monthly spending chart using Recharts
4. THE Dashboard SHALL display category breakdown visualization
5. THE Dashboard SHALL include a "Sync Now" button for manual synchronization
6. THE Dashboard SHALL provide CSV export functionality for transactions
7. THE Frontend SHALL support dark mode toggle
8. THE Transactions page SHALL display a paginated list of all transactions
9. THE Transactions page SHALL allow filtering by date range, transaction type, and merchant
10. THE Settings page SHALL allow users to manage sync preferences and view sync history

### Requirement 7: Security and Data Protection

**User Story:** As a security-conscious user, I want my sensitive data protected with industry-standard security practices, so that my financial information remains confidential.

#### Acceptance Criteria

1. THE Backend SHALL encrypt refresh tokens using Fernet or equivalent encryption before database storage
2. THE System SHALL never expose Google client secrets in frontend code or API responses
3. THE Backend SHALL enforce HTTPS for all API endpoints in production
4. THE Backend SHALL validate JWT tokens on all protected endpoints
5. THE Backend SHALL implement rate limiting on authentication and API endpoints
6. THE Backend SHALL validate and sanitize all user inputs using Pydantic schemas
7. THE Database SHALL use parameterized queries to prevent SQL injection attacks
8. THE Backend SHALL configure CORS to allow only authorized frontend origins
9. WHEN a user logs out, THE Backend SHALL invalidate the session token and clear cookies

### Requirement 8: Data Persistence and Migrations

**User Story:** As a developer, I want database schema versioning and migration support, so that schema changes can be applied safely across environments.

#### Acceptance Criteria

1. THE System SHALL use Alembic for database migrations
2. THE System SHALL include initial migration scripts for all tables
3. WHEN schema changes occur, THE System SHALL provide migration scripts to update the database
4. THE System SHALL support both upgrade and downgrade migrations
5. THE Backend SHALL run pending migrations on application startup in development mode

### Requirement 9: API Design and Documentation

**User Story:** As a frontend developer, I want well-documented REST APIs, so that I can integrate the frontend with the backend efficiently.

#### Acceptance Criteria

1. THE Backend SHALL expose a POST /auth/google endpoint for OAuth callback handling
2. THE Backend SHALL expose a GET /auth/me endpoint to retrieve current user information
3. THE Backend SHALL expose a POST /auth/logout endpoint to terminate user sessions
4. THE Backend SHALL expose a GET /transactions endpoint with pagination, filtering, and sorting
5. THE Backend SHALL expose a POST /sync/manual endpoint to trigger manual synchronization
6. THE Backend SHALL expose a GET /analytics/summary endpoint for dashboard statistics
7. THE Backend SHALL expose a GET /analytics/monthly endpoint for monthly spending data
8. THE Backend SHALL expose a GET /sync/history endpoint for sync log retrieval
9. THE Backend SHALL provide OpenAPI/Swagger documentation at /docs endpoint
10. THE Backend SHALL return consistent error responses with appropriate HTTP status codes

### Requirement 10: Deployment and Configuration

**User Story:** As a DevOps engineer, I want containerized deployment with clear configuration management, so that the application can be deployed consistently across environments.

#### Acceptance Criteria

1. THE System SHALL include a Dockerfile for backend containerization
2. THE System SHALL include a docker-compose.yml file for local development
3. THE System SHALL include a .env.example file documenting all required environment variables
4. THE System SHALL support deployment of Backend to Render or Railway
5. THE System SHALL support deployment of Frontend to Vercel or Netlify
6. THE System SHALL include deployment documentation with step-by-step instructions
7. THE Documentation SHALL include instructions for creating a Neon database
8. THE Documentation SHALL include instructions for enabling Gmail API in Google Cloud Console
9. THE Documentation SHALL include instructions for configuring OAuth 2.0 credentials
10. THE System SHALL validate required environment variables on startup

### Requirement 11: Error Handling and Logging

**User Story:** As a system administrator, I want comprehensive error handling and logging, so that I can diagnose and resolve issues quickly.

#### Acceptance Criteria

1. THE Backend SHALL log all authentication attempts with success/failure status
2. THE Backend SHALL log all Gmail API calls with response status
3. THE Backend SHALL log all email parsing attempts with success/failure details
4. THE Backend SHALL log all database operations errors
5. WHEN an error occurs, THE Backend SHALL return user-friendly error messages
6. THE Backend SHALL log errors with appropriate severity levels (INFO, WARNING, ERROR, CRITICAL)
7. THE Backend SHALL include request correlation IDs for tracing requests across services
8. THE Scheduler SHALL log sync job start, completion, and failure events

### Requirement 12: Performance and Scalability

**User Story:** As a product owner, I want the system to handle multiple concurrent users efficiently, so that the application remains responsive under load.

#### Acceptance Criteria

1. THE Backend SHALL use async/await patterns for all I/O operations
2. THE Database SHALL use connection pooling with appropriate pool size limits
3. THE Backend SHALL implement pagination for transaction list endpoints with maximum 100 items per page
4. THE Frontend SHALL implement lazy loading for transaction lists
5. THE System SHALL cache user session data to minimize database queries
6. THE Scheduler SHALL process users in batches to avoid overwhelming the Gmail API
7. THE Backend SHALL implement request timeout limits to prevent hanging connections

### Requirement 13: Date and Timezone Handling

**User Story:** As a user, I want my transactions to be recorded with accurate dates and times, so that my financial analytics reflect the correct timeline.

#### Acceptance Criteria

1. THE System SHALL use timezone-aware datetime objects (UTC) for all internal date/time storage and operations
2. THE System SHALL store all timestamps in the Database as UTC
3. WHEN calculating date ranges, THE System SHALL use proper month arithmetic (not approximate 30-day months)
4. THE Email_Parser SHALL return None for missing dates rather than using current date as fallback
5. THE System SHALL consistently use UTC for all datetime operations (no mixing of datetime.now() and datetime.utcnow())
6. THE Analytics service SHALL use python-dateutil for accurate month calculations
7. WHEN displaying dates to users, THE Frontend MAY convert UTC to user's local timezone
