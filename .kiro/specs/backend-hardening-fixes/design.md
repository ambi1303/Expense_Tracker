# Backend Hardening Fixes Design

## Overview

This design addresses 20+ critical vulnerabilities, data loss issues, performance problems, and code quality defects in the Gmail Expense Tracker backend. The fixes span security (CSRF protection, JWT cookie handling, error sanitization), data integrity (Gmail pagination, sync locking, incremental sync), async performance (event loop blocking), parsing enhancements (HTML support, currency symbols), feature additions (categorization, UPI extraction, new fields), and code quality improvements (structured logging, SQLAlchemy relationships, field whitelisting).

The approach is systematic: each fix is isolated, testable, and preserves existing functionality. Security fixes prevent CSRF attacks and token leakage. Data integrity fixes ensure no transaction loss from pagination limits or concurrent syncs. Performance fixes eliminate event loop blocking. Parsing enhancements handle real-world bank email formats. Feature additions enable auto-categorization and richer transaction data. Code quality fixes improve maintainability and follow best practices.

## Glossary

- **Bug_Condition (C)**: The set of conditions that trigger each of the 20+ bugs - CSRF vulnerability, JWT in URL, missing pagination, event loop blocking, HTML parsing failure, missing fields, etc.
- **Property (P)**: The desired correct behavior for each bug condition - CSRF state validation, HTTPOnly cookies, paginated fetching, async execution, HTML stripping, field extraction, etc.
- **Preservation**: All existing functionality that must remain unchanged - authentication flow, transaction parsing for plain text emails, analytics calculations, CSV export, etc.
- **CSRF State Store**: In-memory dictionary mapping state tokens to expiration timestamps for OAuth flow validation
- **nextPageToken**: Gmail API pagination token for fetching emails beyond the 100-message limit
- **run_in_executor()**: FastAPI/asyncio method for wrapping synchronous blocking calls to prevent event loop blocking
- **BeautifulSoup**: Python library for parsing and stripping HTML tags from email content
- **Categorization Engine**: Keyword-based system for auto-assigning transaction categories using pattern matching
- **UPI Reference**: Unified Payments Interface transaction ID extracted from Indian bank emails
- **Merchant Normalization**: Case-insensitive grouping of merchant names in analytics (e.g., "AMAZON" = "Amazon" = "amazon")

## Bug Details

### Fault Condition

The bugs manifest across multiple categories:

**Security Vulnerabilities:**
1. OAuth callback accepts any state parameter without validation, enabling CSRF attacks
2. JWT token is exposed in redirect URL (/auth/complete?token=...), leaking to browser history and logs
3. Production errors expose internal stack traces and implementation details to users
4. sort_by parameter accepts arbitrary strings without validation, potentially exposing internal fields

**Data Loss Issues:**
5. Gmail API fetch_transaction_emails() only retrieves first 100 emails, ignoring nextPageToken pagination
6. Scheduled sync fetches ALL emails instead of passing last_sync_time to Gmail API
7. Manual sync allows concurrent execution without locking, causing duplicate processing

**Event Loop Blocking:**
8. Gmail API calls (fetch_transaction_emails, get_email_content) use synchronous googleapiclient, blocking FastAPI event loop
9. refresh_access_token() uses synchronous google.auth.transport.requests.Request(), blocking event loop

**Parsing Failures:**
10. Email parser only handles plain text, fails on HTML-formatted bank emails
11. AMOUNT_PATTERNS don't include ₹ Unicode symbol, missing Indian currency formats
12. _extract_body() doesn't prioritize text/plain over HTML, may return HTML tags

**Missing Functionality:**
13. Transaction model lacks category, payment_method, upi_reference, raw_snippet fields
14. Email parser doesn't extract UPI IDs or payment methods
15. No auto-categorization engine for transactions
16. Analytics merchant grouping is case-sensitive, treating "AMAZON" and "amazon" as different

**Code Quality:**
17. OAuth routes use print() instead of structlog logger
18. conftest.py raw SQL not wrapped with text(), fails on SQLAlchemy 2.0
19. Models lack relationship() definitions, preventing efficient ORM navigation
20. User model doesn't track updated_at timestamp

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type SystemState
  OUTPUT: boolean
  
  RETURN (input.oauthCallback AND NOT input.stateValidated)  // Bug 1
         OR (input.jwtToken IN input.redirectURL)  // Bug 2
         OR (input.errorResponse CONTAINS stackTrace)  // Bug 3
         OR (input.sortByParam NOT IN ALLOWED_FIELDS)  // Bug 4
         OR (input.emailCount > 100 AND NOT input.paginationUsed)  // Bug 5
         OR (input.syncType == "scheduled" AND NOT input.lastSyncTimePassed)  // Bug 6
         OR (input.concurrentSyncRequests > 1 AND NOT input.lockAcquired)  // Bug 7
         OR (input.gmailAPICall AND input.executionContext == "eventLoop")  // Bug 8
         OR (input.tokenRefresh AND input.executionContext == "eventLoop")  // Bug 9
         OR (input.emailFormat == "HTML" AND NOT input.htmlStripped)  // Bug 10
         OR (input.currencySymbol == "₹" AND NOT input.amountExtracted)  // Bug 11
         OR (input.emailHasBothFormats AND input.extractedHTML)  // Bug 12
         OR (input.transactionCreated AND input.categoryField == NULL)  // Bug 13
         OR (input.emailHasUPI AND NOT input.upiExtracted)  // Bug 14
         OR (input.transactionCreated AND NOT input.autoCategorized)  // Bug 15
         OR (input.merchantGrouping AND input.caseSensitive)  // Bug 16
         OR (input.authEvent AND input.logMethod == "print")  // Bug 17
         OR (input.testSQL AND NOT input.textWrapped)  // Bug 18
         OR (input.modelQuery AND NOT input.relationshipDefined)  // Bug 19
         OR (input.userUpdated AND NOT input.updatedAtSet)  // Bug 20
END FUNCTION
```

### Examples


**Security Examples:**
- Bug 1: Attacker crafts OAuth URL with victim's session, bypasses state validation, gains access
- Bug 2: JWT token "eyJhbGc..." appears in browser history at /auth/complete?token=eyJhbGc..., leaked to analytics
- Bug 3: Database connection error exposes "postgresql://user:pass@localhost:5432/db" in production response
- Bug 4: Malicious user sends sort_by=refresh_token_encrypted, potentially exposing sensitive data

**Data Loss Examples:**
- Bug 5: User has 250 bank emails, only first 100 fetched, 150 transactions lost
- Bug 6: Scheduled sync fetches all 10,000 emails every 15 minutes instead of only new ones, wasting API quota
- Bug 7: User clicks "Sync Now" twice rapidly, both syncs process same emails, creating duplicate transactions

**Performance Examples:**
- Bug 8: Gmail API call takes 2 seconds, blocks event loop, all other requests wait
- Bug 9: Token refresh takes 1 second during sync, blocks event loop for all users

**Parsing Examples:**
- Bug 10: HDFC email contains "<p>Amount: Rs 500</p>", parser extracts "Amount: Rs 500" with tags, regex fails
- Bug 11: Email says "₹1,234.56 debited", AMOUNT_PATTERNS don't match ₹, amount extraction fails
- Bug 12: Email has plain text "Rs 500" and HTML "<b>Rs 500</b>", parser returns HTML version with tags

**Feature Examples:**
- Bug 13: Transaction stored without category field, frontend can't filter by category
- Bug 14: Email contains "UPI Ref: 123456789012", parser doesn't extract it, user can't search by UPI ID
- Bug 15: User creates transaction for "Swiggy", system doesn't auto-categorize as "Food"
- Bug 16: Analytics shows "AMAZON" (₹5000) and "Amazon" (₹3000) as separate merchants instead of ₹8000 total

**Code Quality Examples:**
- Bug 17: OAuth callback uses print("User logged in"), logs not structured, can't query in production
- Bug 18: Test executes db.execute("SELECT * FROM users"), fails with "Textual SQL expression should be wrapped with text()"
- Bug 19: Code tries user.transactions to get related transactions, fails because relationship not defined
- Bug 20: User record updated but updated_at still shows old timestamp, can't track when changes occurred

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Users with fewer than 100 emails must continue to sync correctly (Requirement 3.1)
- Plain text bank emails must continue to parse successfully with existing regex patterns (Requirement 3.2)
- Valid JWT tokens must continue to authenticate users correctly (Requirement 3.3)
- Transaction queries with valid filters must continue to return correct results (Requirement 3.4)
- Analytics for valid date ranges must continue to calculate spending trends accurately (Requirement 3.5)
- OAuth flow with valid credentials must continue to create sessions and store tokens (Requirement 3.6)
- Scheduled sync for users with no new emails must continue to complete without errors (Requirement 3.7)
- Transaction amounts in standard formats (Rs., INR) must continue to parse correctly (Requirement 3.8)
- CSV export must continue to generate valid files with existing fields (Requirement 3.9)
- Database queries with existing sort fields must continue to sort correctly (Requirement 3.10)

**Scope:**
All inputs that do NOT involve the specific bug conditions should be completely unaffected by these fixes. This includes:
- Existing authentication flows for users not affected by CSRF attacks
- Email parsing for plain text emails without HTML or ₹ symbols
- Sync operations for users with small email volumes
- Analytics queries that don't group by merchant
- Database operations that don't use raw SQL or relationships

## Hypothesized Root Cause

Based on the bug analysis, the root causes are:

1. **Missing CSRF Protection**: OAuth implementation doesn't generate or validate state parameter, following basic OAuth flow without CSRF protection

2. **JWT in URL Design**: Original design passes JWT as query parameter for frontend to set cookie, but this exposes token to logs and history

3. **Generic Error Handling**: FastAPI default error handling returns full exception details, no production error sanitization

4. **Missing Input Validation**: sort_by parameter directly used in SQLAlchemy order_by() without whitelist validation

5. **Incomplete Pagination Logic**: Gmail API code only calls list() once, doesn't check for nextPageToken or implement loop

6. **Missing Incremental Sync**: Scheduled sync doesn't query last successful sync time or pass after: parameter to Gmail API

7. **No Concurrency Control**: Manual sync endpoint directly calls sync function without checking for in-progress syncs or acquiring locks

8. **Synchronous Gmail Client**: googleapiclient.discovery.build() returns synchronous client, all API calls block

9. **Synchronous Token Refresh**: google.auth.transport.requests.Request() is synchronous, blocks during credentials.refresh()

10. **Plain Text Assumption**: Email parser assumes plain text, doesn't use HTML parsing library

11. **Limited Currency Patterns**: AMOUNT_PATTERNS only include ASCII "Rs" and "INR", don't account for Unicode ₹

12. **No Format Preference**: _extract_body() returns first found body, doesn't prioritize plain text over HTML

13. **Minimal Schema Design**: Initial Transaction model only included essential fields, didn't anticipate categorization needs

14. **Basic Parser Implementation**: Email parser focused on amount/date/merchant, didn't extract payment-specific fields

15. **No Categorization Logic**: System designed for manual categorization, no auto-categorization engine implemented

16. **Direct Merchant Grouping**: Analytics uses Transaction.merchant directly in GROUP BY without case normalization

17. **Debug Logging**: OAuth routes use print() for quick debugging, not replaced with proper logging

18. **SQLAlchemy 1.x Syntax**: Tests written for SQLAlchemy 1.x where raw SQL strings were accepted

19. **Minimal ORM Usage**: Models defined without relationships, queries use manual joins

20. **Static User Model**: User model created without updated_at, no timestamp tracking for modifications

## Correctness Properties

Property 1: Fault Condition - CSRF State Validation

_For any_ OAuth callback request where a state parameter is provided, the fixed system SHALL validate that the state exists in the server-side store, has not expired, matches the provided value, and SHALL reject requests with invalid or missing state parameters, preventing CSRF attacks.

**Validates: Requirements 2.1, 2.2**

Property 2: Fault Condition - JWT HTTPOnly Cookie

_For any_ successful OAuth authentication, the fixed system SHALL set the JWT token as an HTTPOnly secure cookie directly on the RedirectResponse instead of including it in the URL, preventing token leakage to browser history, logs, and Referer headers.

**Validates: Requirements 2.3**

Property 3: Fault Condition - Error Message Sanitization

_For any_ error that occurs in production environment, the fixed system SHALL sanitize error messages to hide internal implementation details, stack traces, and sensitive information, returning only generic user-friendly error messages.

**Validates: Requirements 2.4**

Property 4: Fault Condition - Sort Field Whitelisting

_For any_ transaction query with a sort_by parameter, the fixed system SHALL validate the parameter against an ALLOWED_SORT_FIELDS whitelist and reject requests with invalid fields, preventing exposure of internal database fields.

**Validates: Requirements 2.17**

Property 5: Fault Condition - Gmail Pagination

_For any_ user with more than 100 transaction emails, the fixed system SHALL implement nextPageToken pagination loop with configurable max cap to fetch all emails, preventing data loss from pagination limits.

**Validates: Requirements 2.5**

Property 6: Fault Condition - Incremental Sync

_For any_ scheduled sync operation, the fixed system SHALL query the last successful sync time and pass it to Gmail API using the after: parameter to fetch only new emails, reducing API usage and sync time.

**Validates: Requirements 2.7**

Property 7: Fault Condition - Sync Concurrency Control

_For any_ manual sync request, the fixed system SHALL use per-user asyncio.Lock to prevent concurrent syncs and add rate limiting, preventing duplicate processing and data inconsistencies.

**Validates: Requirements 2.6**

Property 8: Fault Condition - Async Gmail API Calls

_For any_ Gmail API call (fetch_transaction_emails, get_email_content), the fixed system SHALL wrap the synchronous call with run_in_executor() to avoid blocking the FastAPI event loop, maintaining application responsiveness.

**Validates: Requirements 2.8**

Property 9: Fault Condition - Async Token Refresh

_For any_ OAuth token refresh operation, the fixed system SHALL wrap refresh_access_token() with run_in_executor() for async execution, preventing event loop blocking during token refresh.

**Validates: Requirements 2.9**

Property 10: Fault Condition - HTML Email Parsing

_For any_ HTML-formatted bank email, the fixed system SHALL use BeautifulSoup to strip HTML tags before regex operations, enabling successful parsing of HTML emails.

**Validates: Requirements 2.10**

Property 11: Fault Condition - Unicode Currency Support

_For any_ email containing ₹ symbol or other Indian currency formats, the fixed system SHALL update AMOUNT_PATTERNS to include Unicode currency symbols, enabling successful amount extraction.

**Validates: Requirements 2.11**

Property 12: Fault Condition - Plain Text Preference

_For any_ email containing both text/plain and text/html content, the fixed system SHALL prefer text/plain content over HTML when extracting email body, avoiding HTML tag extraction.

**Validates: Requirements 2.12**

Property 13: Fault Condition - Extended Transaction Fields

_For any_ transaction stored in the database, the fixed system SHALL include category, payment_method, upi_reference, and raw_snippet fields with proper Alembic migration, enabling richer transaction data.

**Validates: Requirements 2.13**

Property 14: Fault Condition - UPI and Payment Method Extraction

_For any_ email containing UPI IDs or payment method information, the fixed system SHALL extract these using UPI_PATTERNS and extract_payment_method() function, capturing payment-specific details.

**Validates: Requirements 2.14**

Property 15: Fault Condition - Auto-Categorization

_For any_ transaction created from parsed email, the fixed system SHALL auto-categorize it using keyword-based categorization engine with fuzzy matching for Food, Groceries, Shopping, Transport, Bills, etc., reducing manual categorization effort.

**Validates: Requirements 2.15**

Property 16: Fault Condition - Merchant Normalization

_For any_ analytics query grouping by merchant, the fixed system SHALL use func.lower() for case-insensitive grouping and capitalize output to normalize merchant names, preventing duplicate merchant entries.

**Validates: Requirements 2.16**

Property 17: Fault Condition - Structured Logging

_For any_ authentication event or system operation, the fixed system SHALL use structlog logger instead of print() statements, enabling structured queryable logs in production.

**Validates: Requirements 2.18**

Property 18: Fault Condition - SQLAlchemy 2.0 Compatibility

_For any_ test executing raw SQL, the fixed system SHALL wrap SQL strings with text() wrapper for SQLAlchemy 2.0 compatibility, preventing test failures.

**Validates: Requirements 2.19**

Property 19: Fault Condition - ORM Relationships

_For any_ ORM model query requiring related data, the fixed system SHALL define relationship() definitions for User, Transaction, and SyncLog models, enabling efficient ORM navigation.

**Validates: Requirements 2.20**

Property 20: Fault Condition - User Updated Timestamp

_For any_ user record modification, the fixed system SHALL automatically update the updated_at timestamp, enabling tracking of when user data changed.

**Validates: Requirements 2.21**

Property 21: Preservation - Existing Functionality

_For any_ input that does NOT trigger the bug conditions (plain text emails, small email volumes, valid sort fields, non-concurrent syncs, etc.), the fixed system SHALL produce exactly the same behavior as the original system, preserving all existing functionality.

**Validates: Requirements 3.1-3.10**

## Fix Implementation

### Changes Required

The implementation is organized by category for systematic fixing:


#### Category 1: Security Fixes (Critical)

**File**: `backend/app/auth/oauth.py`

**Changes**:
1. **Add CSRF State Store**: Create in-memory dictionary with TTL for state validation
   ```python
   # At module level
   import secrets
   import time
   from threading import Lock
   
   # In-memory state store: {state: expiration_timestamp}
   _oauth_state_store = {}
   _state_store_lock = Lock()
   STATE_TTL_SECONDS = 600  # 10 minutes
   ```

2. **Update initiate_oauth_flow()**: Generate and store state parameter
   ```python
   # Generate cryptographically secure state
   state = secrets.token_urlsafe(32)
   
   # Store state with expiration
   with _state_store_lock:
       _oauth_state_store[state] = time.time() + STATE_TTL_SECONDS
   
   # Pass state to flow
   authorization_url, _ = flow.authorization_url(
       access_type='offline',
       include_granted_scopes='true',
       prompt='consent',
       state=state  # Add state parameter
   )
   ```

3. **Add validate_and_consume_state()**: Validate state and clean up
   ```python
   def validate_and_consume_state(state: str) -> bool:
       """Validate OAuth state parameter and remove from store."""
       if not state:
           return False
       
       with _state_store_lock:
           # Check if state exists
           if state not in _oauth_state_store:
               return False
           
           # Check if expired
           if time.time() > _oauth_state_store[state]:
               del _oauth_state_store[state]
               return False
           
           # Valid state - consume it (remove from store)
           del _oauth_state_store[state]
           return True
   ```

4. **Add cleanup_expired_states()**: Periodic cleanup function
   ```python
   def cleanup_expired_states():
       """Remove expired states from store."""
       with _state_store_lock:
           current_time = time.time()
           expired = [s for s, exp in _oauth_state_store.items() if current_time > exp]
           for state in expired:
               del _oauth_state_store[state]
   ```

**File**: `backend/app/routes/auth.py`

**Changes**:
1. **Update google_callback()**: Validate state parameter
   ```python
   @router.get("/callback")
   async def google_callback(
       code: str,
       state: str,  # Add state parameter
       response: Response,
       db: AsyncSession = Depends(get_db)
   ):
       # Validate state parameter
       from app.auth.oauth import validate_and_consume_state
       if not validate_and_consume_state(state):
           raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST,
               detail="Invalid or expired state parameter"
           )
       # ... rest of existing code
   ```

2. **Update google_callback()**: Set JWT as HTTPOnly cookie instead of URL
   ```python
   # Generate JWT session token
   session_token = create_session_token(str(user.id), user.email)
   
   # Create redirect response
   frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
   redirect_response = RedirectResponse(url=f"{frontend_url}/dashboard")
   
   # Set HTTPOnly cookie directly on response
   is_production = os.getenv("ENVIRONMENT", "development") == "production"
   redirect_response.set_cookie(
       key="session_token",
       value=session_token,
       httponly=True,
       secure=is_production,
       samesite="lax",
       max_age=7 * 24 * 60 * 60,
       path="/"
   )
   
   return redirect_response
   ```

3. **Replace print() with structlog**: Replace all print statements
   ```python
   # Replace:
   print(f"OAuth ValueError: {str(e)}")
   # With:
   logger.error("oauth_callback_error", error=str(e), error_type="ValueError")
   ```

**File**: `backend/main.py`

**Changes**:
1. **Add production error handler**: Sanitize errors in production
   ```python
   from fastapi import Request, status
   from fastapi.responses import JSONResponse
   import os
   
   @app.exception_handler(Exception)
   async def production_exception_handler(request: Request, exc: Exception):
       """Sanitize error messages in production."""
       is_production = os.getenv("ENVIRONMENT", "development") == "production"
       
       if is_production:
           # Generic error message for production
           return JSONResponse(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               content={"detail": "An internal error occurred. Please try again later."}
           )
       else:
           # Detailed error for development
           import traceback
           return JSONResponse(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               content={
                   "detail": str(exc),
                   "traceback": traceback.format_exc()
               }
           )
   ```

2. **Add state cleanup scheduler**: Schedule periodic cleanup
   ```python
   from apscheduler.schedulers.asyncio import AsyncIOScheduler
   from app.auth.oauth import cleanup_expired_states
   
   @app.on_event("startup")
   async def startup_event():
       # ... existing startup code
       
       # Schedule state cleanup every 5 minutes
       scheduler = AsyncIOScheduler()
       scheduler.add_job(cleanup_expired_states, 'interval', minutes=5)
       scheduler.start()
   ```

**File**: `backend/app/services/transaction_service.py`

**Changes**:
1. **Add sort field whitelist**: Validate sort_by parameter
   ```python
   # At module level
   ALLOWED_SORT_FIELDS = {
       'transaction_date',
       'amount',
       'merchant',
       'bank_name',
       'transaction_type',
       'created_at'
   }
   ```

2. **Update get_transactions()**: Validate sort_by
   ```python
   async def get_transactions(
       db: AsyncSession,
       user_id: UUID,
       filters: Optional[TransactionFilterParams] = None,
       skip: int = 0,
       limit: int = 50,
       sort_by: str = "transaction_date",
       sort_order: str = "desc"
   ) -> tuple[List[Transaction], int]:
       # Validate sort_by parameter
       if sort_by not in ALLOWED_SORT_FIELDS:
           raise ValueError(f"Invalid sort_by field: {sort_by}. Allowed: {ALLOWED_SORT_FIELDS}")
       
       # ... rest of existing code
   ```

#### Category 2: Data Integrity Fixes (Critical)

**File**: `backend/app/services/gmail_service.py`

**Changes**:
1. **Update fetch_transaction_emails()**: Implement pagination loop
   ```python
   async def fetch_transaction_emails(
       access_token: str,
       last_sync_time: Optional[datetime] = None,
       max_results: int = 500  # Configurable cap
   ) -> List[Dict[str, any]]:
       """Fetch transaction emails with pagination support."""
       logger.info("fetch_transaction_emails_started", last_sync_time=last_sync_time)
       
       try:
           service = get_gmail_service(access_token)
           
           # Build search query
           query = TRANSACTION_SEARCH_QUERY
           if last_sync_time:
               date_str = last_sync_time.strftime("%Y/%m/%d")
               query += f" after:{date_str}"
           
           logger.info("gmail_api_search", query=query)
           
           # Pagination loop
           all_messages = []
           next_page_token = None
           
           while len(all_messages) < max_results:
               # Fetch page
               results = service.users().messages().list(
                   userId='me',
                   q=query,
                   maxResults=min(100, max_results - len(all_messages)),
                   pageToken=next_page_token
               ).execute()
               
               messages = results.get('messages', [])
               all_messages.extend(messages)
               
               logger.info("gmail_api_page_fetched", 
                          page_count=len(messages),
                          total_count=len(all_messages))
               
               # Check for next page
               next_page_token = results.get('nextPageToken')
               if not next_page_token:
                   break  # No more pages
           
           logger.info("gmail_api_search_complete", message_count=len(all_messages))
           
           # Fetch full content for each message
           emails = []
           for message in all_messages:
               message_id = message['id']
               try:
                   email_data = await get_email_content(access_token, message_id)
                   emails.append(email_data)
               except Exception as e:
                   logger.error("failed_to_fetch_email_content",
                              message_id=message_id, error=str(e))
                   continue
           
           return emails
           
       except HttpError as e:
           logger.error("gmail_api_error", error=str(e), status_code=e.resp.status)
           raise
   ```

2. **Wrap Gmail API calls with run_in_executor()**: Make async
   ```python
   import asyncio
   from concurrent.futures import ThreadPoolExecutor
   
   # At module level
   _executor = ThreadPoolExecutor(max_workers=10)
   
   async def fetch_transaction_emails(
       access_token: str,
       last_sync_time: Optional[datetime] = None,
       max_results: int = 500
   ) -> List[Dict[str, any]]:
       """Fetch emails asynchronously to avoid blocking event loop."""
       loop = asyncio.get_event_loop()
       
       # Wrap synchronous Gmail API calls in executor
       def _fetch_sync():
           service = get_gmail_service(access_token)
           # ... pagination logic (synchronous)
           return all_messages
       
       all_messages = await loop.run_in_executor(_executor, _fetch_sync)
       
       # Fetch email content asynchronously
       emails = []
       for message in all_messages:
           email_data = await get_email_content(access_token, message['id'])
           emails.append(email_data)
       
       return emails
   ```

3. **Update get_email_content()**: Wrap with run_in_executor()
   ```python
   async def get_email_content(access_token: str, message_id: str) -> Dict[str, any]:
       """Fetch email content asynchronously."""
       loop = asyncio.get_event_loop()
       
       def _get_sync():
           service = get_gmail_service(access_token)
           message = service.users().messages().get(
               userId='me',
               id=message_id,
               format='full'
           ).execute()
           # ... extract headers and body
           return email_data
       
       return await loop.run_in_executor(_executor, _get_sync)
   ```

**File**: `backend/app/auth/oauth.py`

**Changes**:
1. **Wrap refresh_access_token()**: Make async with executor
   ```python
   async def refresh_access_token_async(refresh_token: str) -> str:
       """Async wrapper for token refresh to avoid blocking."""
       loop = asyncio.get_event_loop()
       return await loop.run_in_executor(_executor, refresh_access_token, refresh_token)
   ```

**File**: `backend/app/scheduler/sync_job.py`

**Changes**:
1. **Update sync_user_emails()**: Query last sync time and pass to Gmail API
   ```python
   async def sync_user_emails(user: User, session: AsyncSession) -> dict:
       """Sync emails with incremental fetch support."""
       logger.info("sync_user_emails_started", user_id=str(user.id))
       
       try:
           # Decrypt and refresh access token (async)
           refresh_token = decrypt_refresh_token(user.refresh_token_encrypted)
           from app.auth.oauth import refresh_access_token_async
           access_token = await refresh_access_token_async(refresh_token)
           
           # Query last successful sync time
           last_sync_query = select(SyncLog.created_at).where(
               and_(
                   SyncLog.user_id == user.id,
                   SyncLog.status == "success"
               )
           ).order_by(SyncLog.created_at.desc()).limit(1)
           result = await session.execute(last_sync_query)
           last_sync_time = result.scalar_one_or_none()
           
           logger.info("last_sync_time_queried", 
                      user_id=str(user.id),
                      last_sync_time=last_sync_time)
           
           # Fetch new emails from Gmail (pass last_sync_time)
           emails = await fetch_transaction_emails(access_token, last_sync_time)
           
           # ... rest of processing logic
   ```

2. **Add per-user sync locks**: Prevent concurrent syncs
   ```python
   # At module level
   from asyncio import Lock
   from typing import Dict
   from uuid import UUID
   
   # Per-user sync locks
   _user_sync_locks: Dict[UUID, Lock] = {}
   _locks_dict_lock = Lock()
   
   async def get_user_sync_lock(user_id: UUID) -> Lock:
       """Get or create sync lock for user."""
       async with _locks_dict_lock:
           if user_id not in _user_sync_locks:
               _user_sync_locks[user_id] = Lock()
           return _user_sync_locks[user_id]
   
   async def sync_user_emails(user: User, session: AsyncSession) -> dict:
       """Sync emails with concurrency control."""
       # Acquire user-specific lock
       lock = await get_user_sync_lock(user.id)
       
       if lock.locked():
           logger.warning("sync_already_in_progress", user_id=str(user.id))
           return {
               'success': False,
               'emails_processed': 0,
               'transactions_created': 0,
               'error': 'Sync already in progress for this user'
           }
       
       async with lock:
           # ... existing sync logic
   ```

**File**: `backend/app/routes/sync.py`

**Changes**:
1. **Add rate limiting**: Prevent rapid sync requests
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   
   limiter = Limiter(key_func=get_remote_address)
   
   @router.post("/manual", response_model=SyncResponse)
   @limiter.limit("3/minute")  # Max 3 syncs per minute
   async def trigger_manual_sync(
       request: Request,  # Add request for rate limiter
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       # ... existing code
   ```


#### Category 3: Parsing Enhancements (High Priority)

**File**: `backend/app/services/email_parser.py`

**Changes**:
1. **Update _strip_html()**: Use BeautifulSoup for robust HTML stripping
   ```python
   from bs4 import BeautifulSoup
   
   def _strip_html(text: str) -> str:
       """Strip HTML tags using BeautifulSoup."""
       # Decode HTML entities first
       text = html.unescape(text)
       
       # Use BeautifulSoup to strip HTML tags
       soup = BeautifulSoup(text, 'html.parser')
       text = soup.get_text(separator=' ', strip=True)
       
       # Clean up multiple spaces
       text = re.sub(r'\s+', ' ', text)
       
       return text.strip()
   ```

2. **Update AMOUNT_PATTERNS**: Add ₹ Unicode symbol support
   ```python
   AMOUNT_PATTERNS = [
       r'(?:INR|Rs\.?|₹)\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
       r'(?:amount|Amount|AMOUNT):\s*(?:INR|Rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
       r'(?:debited|credited)\s+(?:with\s+)?(?:INR|Rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
       r'(?:INR|Rs\.?|₹)(\d+(?:,\d+)*(?:\.\d{2})?)',
   ]
   ```

**File**: `backend/app/services/gmail_service.py`

**Changes**:
1. **Update _extract_body()**: Prioritize text/plain over HTML
   ```python
   def _extract_body(payload: Dict) -> str:
       """Extract email body, prioritizing plain text over HTML."""
       plain_text_parts = []
       html_parts = []
       
       def _collect_parts(payload_part):
           """Recursively collect text parts."""
           mime_type = payload_part.get('mimeType', '')
           
           # Extract body data
           if 'body' in payload_part and 'data' in payload_part['body']:
               body_data = payload_part['body']['data']
               body_text = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
               
               if 'text/plain' in mime_type:
                   plain_text_parts.append(body_text)
               elif 'text/html' in mime_type:
                   html_parts.append(body_text)
           
           # Recurse into parts
           if 'parts' in payload_part:
               for part in payload_part['parts']:
                   _collect_parts(part)
       
       _collect_parts(payload)
       
       # Prefer plain text over HTML
       if plain_text_parts:
           return '\n'.join(plain_text_parts).strip()
       elif html_parts:
           # Strip HTML tags from HTML parts
           from app.services.email_parser import _strip_html
           return '\n'.join(_strip_html(html) for html in html_parts).strip()
       else:
           return ""
   ```

#### Category 4: Feature Additions (High Priority)

**File**: `backend/app/models/transaction.py`

**Changes**:
1. **Add new fields to Transaction model**:
   ```python
   class Transaction(Base):
       # ... existing fields
       
       # New fields
       category = Column(String(100), nullable=True, index=True)
       payment_method = Column(String(50), nullable=True)  # UPI, Card, NetBanking, etc.
       upi_reference = Column(String(255), nullable=True, index=True)
       raw_snippet = Column(String(500), nullable=True)  # First 500 chars of email for debugging
   ```

**File**: `backend/alembic/versions/`

**New Migration File**: `YYYYMMDD_add_transaction_fields.py`
```python
"""Add category, payment_method, upi_reference, raw_snippet to transactions

Revision ID: <generated>
Revises: <previous>
Create Date: <timestamp>
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('transactions', sa.Column('category', sa.String(100), nullable=True))
    op.add_column('transactions', sa.Column('payment_method', sa.String(50), nullable=True))
    op.add_column('transactions', sa.Column('upi_reference', sa.String(255), nullable=True))
    op.add_column('transactions', sa.Column('raw_snippet', sa.String(500), nullable=True))
    
    # Add indexes
    op.create_index('ix_transactions_category', 'transactions', ['category'])
    op.create_index('ix_transactions_upi_reference', 'transactions', ['upi_reference'])

def downgrade():
    op.drop_index('ix_transactions_upi_reference', 'transactions')
    op.drop_index('ix_transactions_category', 'transactions')
    op.drop_column('transactions', 'raw_snippet')
    op.drop_column('transactions', 'upi_reference')
    op.drop_column('transactions', 'payment_method')
    op.drop_column('transactions', 'category')
```

**File**: `backend/app/services/email_parser.py`

**Changes**:
1. **Add UPI extraction patterns**:
   ```python
   # UPI patterns for Indian payment systems
   UPI_PATTERNS = [
       r'UPI\s*(?:Ref|Reference|ID|Transaction)[\s:]*([A-Za-z0-9]{12,})',
       r'UPI\s*(?:Txn|Trans)[\s:]*([A-Za-z0-9]{12,})',
       r'(?:Ref|Reference)\s*(?:No|Number)?[\s:]*([A-Za-z0-9]{12,})',
   ]
   
   # Payment method keywords
   PAYMENT_METHOD_KEYWORDS = {
       'UPI': ['upi', 'paytm', 'phonepe', 'googlepay', 'gpay', 'bhim'],
       'Card': ['card', 'debit card', 'credit card', 'visa', 'mastercard', 'rupay'],
       'NetBanking': ['netbanking', 'net banking', 'online banking', 'internet banking'],
       'Wallet': ['wallet', 'paytm wallet', 'phonepe wallet'],
       'Cash': ['cash', 'atm withdrawal', 'atm'],
   }
   ```

2. **Add extraction functions**:
   ```python
   def extract_upi_reference(text: str) -> Optional[str]:
       """Extract UPI reference ID from text."""
       for pattern in UPI_PATTERNS:
           match = re.search(pattern, text, re.IGNORECASE)
           if match:
               upi_ref = match.group(1).strip()
               # Validate length (UPI refs are typically 12+ chars)
               if len(upi_ref) >= 12:
                   logger.debug("upi_reference_extracted", upi_ref=upi_ref)
                   return upi_ref
       return None
   
   def extract_payment_method(text: str) -> Optional[str]:
       """Identify payment method from text."""
       text_lower = text.lower()
       
       for method, keywords in PAYMENT_METHOD_KEYWORDS.items():
           for keyword in keywords:
               if keyword in text_lower:
                   logger.debug("payment_method_extracted", method=method)
                   return method
       
       return None
   ```

3. **Update ParsedTransaction model**:
   ```python
   class ParsedTransaction(BaseModel):
       amount: Decimal
       currency: str = "INR"
       transaction_type: TransactionType
       merchant: Optional[str] = None
       transaction_date: datetime
       bank_name: Optional[str] = None
       category: Optional[str] = None  # New
       payment_method: Optional[str] = None  # New
       upi_reference: Optional[str] = None  # New
       raw_snippet: Optional[str] = None  # New
   ```

4. **Update parse_email()**: Extract new fields
   ```python
   def parse_email(subject: str, body: str) -> Optional[ParsedTransaction]:
       """Parse email with enhanced field extraction."""
       # ... existing parsing logic
       
       # Extract new fields
       upi_reference = extract_upi_reference(text)
       payment_method = extract_payment_method(text)
       
       # Create raw snippet (first 500 chars)
       raw_snippet = text[:500] if len(text) > 500 else text
       
       # Auto-categorize
       category = auto_categorize(merchant, text)
       
       parsed = ParsedTransaction(
           amount=amount,
           currency="INR",
           transaction_type=transaction_type,
           merchant=merchant,
           transaction_date=transaction_date,
           bank_name=bank_name,
           category=category,
           payment_method=payment_method,
           upi_reference=upi_reference,
           raw_snippet=raw_snippet
       )
       
       return parsed
   ```

5. **Add auto-categorization engine**:
   ```python
   from difflib import SequenceMatcher
   
   # Category keyword mappings
   CATEGORY_KEYWORDS = {
       'Food': [
           'swiggy', 'zomato', 'uber eats', 'dominos', 'pizza', 'restaurant',
           'cafe', 'food', 'mcdonald', 'kfc', 'subway', 'starbucks'
       ],
       'Groceries': [
           'bigbasket', 'grofers', 'blinkit', 'dunzo', 'dmart', 'reliance fresh',
           'more', 'supermarket', 'grocery', 'vegetables', 'fruits'
       ],
       'Shopping': [
           'amazon', 'flipkart', 'myntra', 'ajio', 'nykaa', 'shopping',
           'mall', 'store', 'retail'
       ],
       'Transport': [
           'uber', 'ola', 'rapido', 'metro', 'bus', 'taxi', 'fuel',
           'petrol', 'diesel', 'parking', 'toll'
       ],
       'Bills': [
           'electricity', 'water', 'gas', 'internet', 'broadband', 'mobile',
           'recharge', 'bill payment', 'utility'
       ],
       'Entertainment': [
           'netflix', 'amazon prime', 'hotstar', 'spotify', 'movie', 'cinema',
           'theatre', 'gaming', 'subscription'
       ],
       'Healthcare': [
           'pharmacy', 'hospital', 'clinic', 'doctor', 'medicine', 'medical',
           'health', 'apollo', 'medplus'
       ],
       'Education': [
           'school', 'college', 'university', 'course', 'tuition', 'books',
           'education', 'learning'
       ],
   }
   
   def fuzzy_match(text: str, keyword: str, threshold: float = 0.8) -> bool:
       """Check if text fuzzy matches keyword."""
       ratio = SequenceMatcher(None, text.lower(), keyword.lower()).ratio()
       return ratio >= threshold
   
   def auto_categorize(merchant: Optional[str], text: str) -> Optional[str]:
       """Auto-categorize transaction based on merchant and text."""
       if not merchant and not text:
           return None
       
       search_text = f"{merchant or ''} {text}".lower()
       
       # Exact keyword matching
       for category, keywords in CATEGORY_KEYWORDS.items():
           for keyword in keywords:
               if keyword in search_text:
                   logger.debug("category_matched_exact", 
                              category=category, keyword=keyword)
                   return category
       
       # Fuzzy matching on merchant name
       if merchant:
           for category, keywords in CATEGORY_KEYWORDS.items():
               for keyword in keywords:
                   if fuzzy_match(merchant, keyword, threshold=0.75):
                       logger.debug("category_matched_fuzzy",
                                  category=category, keyword=keyword)
                       return category
       
       return None
   ```

**File**: `backend/app/services/transaction_service.py`

**Changes**:
1. **Update create_transaction()**: Store new fields
   ```python
   async def create_transaction(
       db: AsyncSession,
       user_id: UUID,
       parsed_transaction: ParsedTransaction,
       message_id: str
   ) -> Optional[Transaction]:
       """Create transaction with enhanced fields."""
       # ... existing validation
       
       transaction = Transaction(
           user_id=user_id,
           amount=parsed_transaction.amount,
           currency=parsed_transaction.currency,
           transaction_type=parsed_transaction.transaction_type.value,
           merchant=parsed_transaction.merchant,
           transaction_date=parsed_transaction.transaction_date,
           bank_name=parsed_transaction.bank_name,
           gmail_message_id=message_id,
           # New fields
           category=parsed_transaction.category,
           payment_method=parsed_transaction.payment_method,
           upi_reference=parsed_transaction.upi_reference,
           raw_snippet=parsed_transaction.raw_snippet
       )
       
       # ... rest of logic
   ```

**File**: `backend/app/services/analytics_service.py`

**Changes**:
1. **Update get_category_breakdown()**: Normalize merchant names
   ```python
   async def get_category_breakdown(
       db: AsyncSession,
       user_id: UUID,
       limit: int = 10
   ) -> List[CategoryDataPoint]:
       """Get spending breakdown with normalized merchant names."""
       # ... existing total query
       
       # Query with case-insensitive grouping
       query = select(
           func.lower(Transaction.merchant).label('merchant_lower'),
           func.sum(Transaction.amount).label('amount'),
           func.count(Transaction.id).label('transaction_count')
       ).where(
           and_(
               Transaction.user_id == user_id,
               Transaction.transaction_type == "debit",
               Transaction.merchant.isnot(None)
           )
       ).group_by(
           func.lower(Transaction.merchant)
       ).order_by(
           func.sum(Transaction.amount).desc()
       ).limit(limit)
       
       result = await db.execute(query)
       rows = result.all()
       
       # Convert to CategoryDataPoint with capitalized merchant names
       categories = []
       for row in rows:
           amount = float(row.amount)
           percentage = (amount / total_spent * 100) if total_spent > 0 else 0
           
           # Capitalize merchant name for display
           merchant_display = row.merchant_lower.capitalize()
           
           categories.append(CategoryDataPoint(
               merchant=merchant_display,
               amount=Decimal(str(amount)),
               transaction_count=row.transaction_count,
               percentage=round(percentage, 2)
           ))
       
       return categories
   ```

#### Category 5: Code Quality Fixes (Medium Priority)

**File**: `backend/app/models/user.py`

**Changes**:
1. **Add updated_at field**:
   ```python
   from sqlalchemy import Column, String, DateTime, Index
   from sqlalchemy.orm import validates
   
   class User(Base):
       # ... existing fields
       
       updated_at = Column(
           DateTime(timezone=True),
           default=lambda: datetime.now(timezone.utc),
           onupdate=lambda: datetime.now(timezone.utc),
           nullable=False
       )
   ```

**File**: `backend/alembic/versions/`

**New Migration File**: `YYYYMMDD_add_user_updated_at.py`
```python
"""Add updated_at to users

Revision ID: <generated>
Revises: <previous>
Create Date: <timestamp>
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

def upgrade():
    # Add column with default value
    op.add_column('users', 
        sa.Column('updated_at', 
                 sa.DateTime(timezone=True),
                 nullable=False,
                 server_default=sa.text('CURRENT_TIMESTAMP'))
    )

def downgrade():
    op.drop_column('users', 'updated_at')
```

**File**: `backend/app/models/user.py`, `backend/app/models/transaction.py`, `backend/app/models/sync_log.py`

**Changes**:
1. **Add SQLAlchemy relationships**:
   ```python
   # In user.py
   from sqlalchemy.orm import relationship
   
   class User(Base):
       # ... existing fields
       
       # Relationships
       transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
       sync_logs = relationship("SyncLog", back_populates="user", cascade="all, delete-orphan")
   
   # In transaction.py
   from sqlalchemy.orm import relationship
   
   class Transaction(Base):
       # ... existing fields
       
       # Relationship
       user = relationship("User", back_populates="transactions")
   
   # In sync_log.py
   from sqlalchemy.orm import relationship
   
   class SyncLog(Base):
       # ... existing fields
       
       # Relationship
       user = relationship("User", back_populates="sync_logs")
   ```

**File**: `backend/tests/conftest.py`

**Changes**:
1. **Wrap raw SQL with text()**:
   ```python
   from sqlalchemy import text
   
   # Replace all raw SQL strings like:
   await db.execute("DELETE FROM transactions")
   
   # With:
   await db.execute(text("DELETE FROM transactions"))
   ```

**File**: `backend/requirements.txt`

**Changes**:
1. **Add beautifulsoup4 dependency**:
   ```
   # Add to requirements.txt
   beautifulsoup4==4.12.2
   lxml==4.9.3  # Parser for BeautifulSoup
   ```


### Summary of Files to Modify

**Modified Files (15)**:
1. `backend/app/auth/oauth.py` - CSRF state store, async token refresh
2. `backend/app/routes/auth.py` - State validation, HTTPOnly cookie, structured logging
3. `backend/main.py` - Production error handler, state cleanup scheduler
4. `backend/app/services/transaction_service.py` - Sort field whitelist
5. `backend/app/services/gmail_service.py` - Pagination, async wrappers, body extraction
6. `backend/app/scheduler/sync_job.py` - Incremental sync, concurrency locks
7. `backend/app/routes/sync.py` - Rate limiting
8. `backend/app/services/email_parser.py` - HTML stripping, ₹ support, UPI extraction, categorization
9. `backend/app/models/transaction.py` - New fields, relationships
10. `backend/app/models/user.py` - updated_at field, relationships
11. `backend/app/models/sync_log.py` - Relationships
12. `backend/app/services/analytics_service.py` - Merchant normalization
13. `backend/tests/conftest.py` - text() wrapper for raw SQL
14. `backend/requirements.txt` - Add beautifulsoup4, lxml
15. `backend/app/routes/transactions.py` - Handle new fields in responses

**New Files (2)**:
1. `backend/alembic/versions/YYYYMMDD_add_transaction_fields.py` - Migration for transaction fields
2. `backend/alembic/versions/YYYYMMDD_add_user_updated_at.py` - Migration for user updated_at

**Schema Changes (2 migrations)**:
1. Add category, payment_method, upi_reference, raw_snippet to transactions table
2. Add updated_at to users table

## Testing Strategy

### Validation Approach

The testing strategy follows a three-phase approach: exploratory testing on unfixed code to confirm bugs, fix verification to ensure bugs are resolved, and preservation testing to ensure existing functionality remains intact.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate each bug BEFORE implementing fixes. Confirm or refute root cause analysis.

**Test Plan**: Write tests that trigger each bug condition on UNFIXED code to observe failures and understand root causes.

**Test Cases**:

1. **CSRF Attack Test**: Simulate OAuth callback with forged state parameter (will succeed on unfixed code, should fail after fix)
2. **JWT Leakage Test**: Complete OAuth flow and verify JWT appears in redirect URL (will leak on unfixed code)
3. **Error Exposure Test**: Trigger database error and verify stack trace in response (will expose on unfixed code)
4. **Sort Injection Test**: Send sort_by=refresh_token_encrypted and verify it's accepted (will accept on unfixed code)
5. **Pagination Loss Test**: Create 150 test emails, verify only 100 fetched (will lose 50 on unfixed code)
6. **Full Sync Test**: Trigger scheduled sync twice, verify it fetches all emails both times (will duplicate on unfixed code)
7. **Concurrent Sync Test**: Trigger two manual syncs simultaneously, verify both execute (will duplicate on unfixed code)
8. **Event Loop Blocking Test**: Monitor event loop during Gmail API call, verify blocking (will block on unfixed code)
9. **HTML Parsing Test**: Send HTML email with "<p>Rs 500</p>", verify parsing fails (will fail on unfixed code)
10. **₹ Symbol Test**: Send email with "₹1,234.56 debited", verify amount extraction fails (will fail on unfixed code)
11. **HTML Priority Test**: Send email with both plain text and HTML, verify HTML extracted (will extract HTML on unfixed code)
12. **Missing Fields Test**: Create transaction, verify category/payment_method/upi_reference are NULL (will be NULL on unfixed code)
13. **UPI Extraction Test**: Send email with UPI reference, verify not extracted (will not extract on unfixed code)
14. **Categorization Test**: Create transaction for "Swiggy", verify category is NULL (will be NULL on unfixed code)
15. **Merchant Case Test**: Create transactions for "AMAZON" and "amazon", verify counted separately (will separate on unfixed code)
16. **Print Logging Test**: Trigger OAuth callback, verify print() used instead of logger (will use print on unfixed code)
17. **Raw SQL Test**: Execute raw SQL in test, verify SQLAlchemy 2.0 error (will fail on unfixed code)
18. **Relationship Test**: Try to access user.transactions, verify AttributeError (will fail on unfixed code)
19. **Updated At Test**: Update user record, verify updated_at unchanged (will not update on unfixed code)

**Expected Counterexamples**:
- CSRF attacks succeed without state validation
- JWT tokens leak to browser history and logs
- Internal errors expose stack traces and credentials
- Arbitrary sort fields accepted, potentially exposing sensitive data
- Pagination stops at 100 emails, losing transactions
- Scheduled syncs fetch all emails repeatedly, wasting API quota
- Concurrent syncs process duplicate emails
- Gmail API calls block event loop, degrading performance
- HTML emails fail to parse, losing transactions
- ₹ symbol amounts not extracted, losing transactions
- HTML content extracted instead of plain text
- New fields not captured in database
- UPI references not extracted
- Transactions not auto-categorized
- Merchant names not normalized in analytics
- Logs use print() instead of structured logging
- Raw SQL fails on SQLAlchemy 2.0
- ORM relationships not defined
- User updated_at not tracked

### Fix Checking

**Goal**: Verify that for all inputs where bug conditions hold, the fixed system produces expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixedSystem(input)
  ASSERT expectedBehavior(result)
END FOR
```

**Test Categories**:

1. **Security Fix Tests**:
   - Test CSRF state validation rejects invalid states
   - Test JWT set as HTTPOnly cookie, not in URL
   - Test production errors sanitized
   - Test sort_by whitelist rejects invalid fields

2. **Data Integrity Fix Tests**:
   - Test pagination fetches all emails beyond 100
   - Test incremental sync only fetches new emails
   - Test concurrent sync prevention with locks
   - Test async Gmail API calls don't block event loop
   - Test async token refresh doesn't block event loop

3. **Parsing Enhancement Tests**:
   - Test HTML emails parsed correctly
   - Test ₹ symbol amounts extracted
   - Test plain text preferred over HTML

4. **Feature Addition Tests**:
   - Test new fields stored in database
   - Test UPI references extracted
   - Test transactions auto-categorized
   - Test merchant names normalized

5. **Code Quality Tests**:
   - Test structured logging used
   - Test raw SQL wrapped with text()
   - Test ORM relationships work
   - Test updated_at tracked

### Preservation Checking

**Goal**: Verify that for all inputs where bug conditions do NOT hold, the fixed system produces the same result as the original system.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalSystem(input) = fixedSystem(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for non-bug scenarios, then write property-based tests capturing that behavior.

**Test Cases**:

1. **Small Email Volume Preservation**: Users with <100 emails continue to sync correctly
2. **Plain Text Email Preservation**: Plain text emails continue to parse with existing patterns
3. **Valid JWT Preservation**: Valid JWT tokens continue to authenticate correctly
4. **Valid Filter Preservation**: Transaction queries with valid filters continue to work
5. **Analytics Preservation**: Analytics calculations continue to be accurate
6. **OAuth Success Preservation**: Valid OAuth flows continue to create sessions
7. **No New Emails Preservation**: Scheduled syncs with no new emails continue to complete
8. **Standard Currency Preservation**: Rs. and INR amounts continue to parse correctly
9. **CSV Export Preservation**: CSV exports continue to generate valid files
10. **Valid Sort Preservation**: Queries with valid sort fields continue to sort correctly

### Unit Tests

**Security Tests**:
- Test state generation creates unique tokens
- Test state validation rejects expired states
- Test state validation rejects invalid states
- Test state cleanup removes expired entries
- Test HTTPOnly cookie set correctly
- Test production error sanitization
- Test sort_by whitelist validation

**Data Integrity Tests**:
- Test pagination loop fetches multiple pages
- Test pagination stops at max_results cap
- Test incremental sync passes last_sync_time
- Test sync lock prevents concurrent execution
- Test rate limiting blocks rapid requests
- Test async wrappers don't block event loop

**Parsing Tests**:
- Test BeautifulSoup strips HTML tags
- Test ₹ symbol in AMOUNT_PATTERNS
- Test plain text preferred over HTML
- Test UPI pattern matching
- Test payment method extraction
- Test auto-categorization keyword matching
- Test fuzzy matching for categorization

**Feature Tests**:
- Test new fields stored in database
- Test migration adds columns correctly
- Test migration rollback removes columns
- Test merchant normalization in analytics
- Test updated_at timestamp updates

**Code Quality Tests**:
- Test structlog logger used instead of print
- Test text() wrapper for raw SQL
- Test ORM relationships defined
- Test relationship cascade deletes

### Property-Based Tests

**Security Properties**:
- Generate random state tokens, verify all validated correctly
- Generate random OAuth callbacks, verify CSRF protection
- Generate random errors, verify sanitization in production

**Data Integrity Properties**:
- Generate random email counts (0-1000), verify all fetched with pagination
- Generate random sync times, verify incremental fetch
- Generate concurrent sync requests, verify only one executes

**Parsing Properties**:
- Generate random HTML emails, verify parsing succeeds
- Generate random currency formats with ₹, verify extraction
- Generate emails with both formats, verify plain text preferred

**Feature Properties**:
- Generate random transactions, verify auto-categorization
- Generate random merchant names with different cases, verify normalization
- Generate random UPI references, verify extraction

**Preservation Properties**:
- Generate random valid inputs, verify behavior unchanged from original
- Generate random plain text emails, verify parsing unchanged
- Generate random small email volumes, verify sync unchanged

### Integration Tests

**End-to-End Security Flow**:
- Complete OAuth flow with state validation
- Verify JWT cookie set and authentication works
- Trigger error and verify sanitization

**End-to-End Data Integrity Flow**:
- Create 200 test emails in Gmail
- Trigger sync and verify all 200 fetched
- Trigger second sync and verify only new emails fetched
- Trigger concurrent syncs and verify lock prevents duplicates

**End-to-End Parsing Flow**:
- Send HTML email with ₹ symbol
- Verify parsing succeeds and transaction created
- Verify all new fields populated correctly

**End-to-End Feature Flow**:
- Create transaction for known merchant (e.g., "Swiggy")
- Verify auto-categorized as "Food"
- Query analytics and verify merchant normalized
- Verify UPI reference searchable

**End-to-End Code Quality Flow**:
- Trigger authentication events
- Verify structured logs generated
- Query user with relationships
- Verify updated_at tracked

### Performance Tests

**Event Loop Blocking Tests**:
- Measure event loop latency during Gmail API calls
- Verify latency <10ms with async wrappers
- Measure concurrent request throughput
- Verify throughput maintained during sync

**Pagination Performance Tests**:
- Measure sync time for 100 vs 500 emails
- Verify linear scaling with pagination
- Measure API quota usage
- Verify incremental sync reduces quota usage by 90%+

**Categorization Performance Tests**:
- Measure categorization time for 1000 transactions
- Verify <1ms per transaction
- Measure fuzzy matching overhead
- Verify acceptable performance

### Migration Tests

**Schema Migration Tests**:
- Test upgrade adds columns correctly
- Test downgrade removes columns correctly
- Test data preserved during migration
- Test indexes created correctly
- Test foreign keys maintained

**Data Migration Tests**:
- Test existing transactions unaffected
- Test existing users unaffected
- Test new fields default to NULL
- Test updated_at defaults to current timestamp

