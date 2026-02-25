# Implementation Plan

## Overview
This plan addresses 20+ critical fixes across security, data integrity, performance, parsing, and code quality. Tasks are organized by priority with clear dependencies. Each category includes exploration tests (before fix), preservation tests (before fix), and implementation with verification.

## Task Organization
- Tasks 1-4: Security exploration and preservation tests (BEFORE fixes)
- Tasks 5-8: Data integrity exploration and preservation tests (BEFORE fixes)
- Tasks 9-12: Performance and parsing exploration tests (BEFORE fixes)
- Tasks 13-16: Feature and quality exploration tests (BEFORE fixes)
- Tasks 17-20: Security fixes implementation
- Tasks 21-24: Data integrity fixes implementation
- Tasks 25-28: Performance and parsing fixes implementation
- Tasks 29-32: Feature additions implementation
- Tasks 33-36: Code quality fixes implementation
- Task 37: Final checkpoint

---

## Phase 1: Exploration Tests (Run on UNFIXED Code)

### Category 1: Security Vulnerabilities Exploration

- [ ] 1. Write security bug exploration tests (BEFORE implementing fixes)
  - **Property 1: Fault Condition** - Security Vulnerabilities
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failures confirm the bugs exist
  - **DO NOT attempt to fix the tests or the code when they fail**
  - **GOAL**: Surface counterexamples demonstrating security vulnerabilities
  - Test 1.1: CSRF Attack - Simulate OAuth callback with forged state parameter (should succeed on unfixed code)
  - Test 1.2: JWT Leakage - Complete OAuth flow and verify JWT appears in redirect URL (will leak on unfixed code)
  - Test 1.3: Error Exposure - Trigger database error and verify stack trace in production response (will expose on unfixed code)
  - Test 1.4: Sort Injection - Send sort_by=refresh_token_encrypted and verify it's accepted (will accept on unfixed code)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: All tests FAIL (this is correct - proves bugs exist)
  - Document counterexamples: CSRF succeeds, JWT in URL, stack traces exposed, arbitrary sort fields accepted
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4_


### Category 2: Data Loss Issues Exploration

- [ ] 2. Write data loss bug exploration tests (BEFORE implementing fixes)
  - **Property 1: Fault Condition** - Data Loss Issues
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failures confirm the bugs exist
  - **GOAL**: Surface counterexamples demonstrating data loss
  - Test 2.1: Pagination Loss - Create 150 test emails, verify only 100 fetched (will lose 50 on unfixed code)
  - Test 2.2: Full Sync Waste - Trigger scheduled sync twice, verify it fetches all emails both times (will duplicate on unfixed code)
  - Test 2.3: Concurrent Sync - Trigger two manual syncs simultaneously, verify both execute (will duplicate on unfixed code)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (confirms pagination stops at 100, no incremental sync, no concurrency control)
  - Document counterexamples: 50 emails lost, all emails fetched repeatedly, concurrent syncs both run
  - _Requirements: 1.4, 1.5, 1.6, 2.5, 2.6, 2.7_

- [ ] 3. Write event loop blocking exploration tests (BEFORE implementing fixes)
  - **Property 1: Fault Condition** - Event Loop Blocking
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failures confirm blocking exists
  - **GOAL**: Demonstrate event loop blocking during Gmail API calls
  - Test 3.1: Gmail API Blocking - Monitor event loop during Gmail API call, verify blocking >100ms (will block on unfixed code)
  - Test 3.2: Token Refresh Blocking - Monitor event loop during token refresh, verify blocking >50ms (will block on unfixed code)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (confirms synchronous calls block event loop)
  - Document counterexamples: Event loop blocked for 2+ seconds during Gmail API calls
  - _Requirements: 1.7, 1.8, 2.8, 2.9_

### Category 3: Parsing Failures Exploration

- [ ] 4. Write parsing bug exploration tests (BEFORE implementing fixes)
  - **Property 1: Fault Condition** - Parsing Failures
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failures confirm parsing bugs
  - **GOAL**: Surface counterexamples demonstrating parsing failures
  - Test 4.1: HTML Parsing - Send HTML email with "<p>Rs 500</p>", verify parsing fails (will fail on unfixed code)
  - Test 4.2: ₹ Symbol - Send email with "₹1,234.56 debited", verify amount extraction fails (will fail on unfixed code)
  - Test 4.3: HTML Priority - Send email with both plain text and HTML, verify HTML extracted instead of plain text (will extract HTML on unfixed code)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (confirms HTML not stripped, ₹ not supported, HTML preferred over plain text)
  - Document counterexamples: HTML emails unparsed, ₹ amounts missed, HTML tags in extracted text
  - _Requirements: 1.9, 1.10, 1.11, 2.10, 2.11, 2.12_

### Category 4: Missing Functionality Exploration

- [ ] 5. Write missing functionality exploration tests (BEFORE implementing fixes)
  - **Property 1: Fault Condition** - Missing Functionality
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failures confirm missing features
  - **GOAL**: Demonstrate missing fields, extraction, and categorization
  - Test 5.1: Missing Fields - Create transaction, verify category/payment_method/upi_reference are NULL (will be NULL on unfixed code)
  - Test 5.2: UPI Extraction - Send email with UPI reference, verify not extracted (will not extract on unfixed code)
  - Test 5.3: Auto-Categorization - Create transaction for "Swiggy", verify category is NULL (will be NULL on unfixed code)
  - Test 5.4: Merchant Case Sensitivity - Create transactions for "AMAZON" and "amazon", verify counted separately in analytics (will separate on unfixed code)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (confirms fields missing, no UPI extraction, no categorization, case-sensitive merchants)
  - Document counterexamples: NULL fields, UPI not extracted, no auto-categorization, duplicate merchants
  - _Requirements: 1.12, 1.13, 1.14, 1.15, 2.13, 2.14, 2.15, 2.16_

### Category 5: Code Quality Issues Exploration

- [ ] 6. Write code quality bug exploration tests (BEFORE implementing fixes)
  - **Property 1: Fault Condition** - Code Quality Issues
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failures confirm quality issues
  - **GOAL**: Demonstrate logging, SQL, relationship, and timestamp issues
  - Test 6.1: Print Logging - Trigger OAuth callback, verify print() used instead of structlog (will use print on unfixed code)
  - Test 6.2: Raw SQL - Execute raw SQL in test, verify SQLAlchemy 2.0 error (will fail on unfixed code)
  - Test 6.3: Missing Relationships - Try to access user.transactions, verify AttributeError (will fail on unfixed code)
  - Test 6.4: Updated At - Update user record, verify updated_at unchanged (will not update on unfixed code)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (confirms print() used, raw SQL fails, no relationships, updated_at not tracked)
  - Document counterexamples: print() statements, SQLAlchemy errors, AttributeError, stale timestamps
  - _Requirements: 1.16, 1.17, 1.18, 1.19, 1.20, 2.17, 2.18, 2.19, 2.20, 2.21_

---

## Phase 2: Preservation Tests (Run on UNFIXED Code)

- [ ] 7. Write preservation property tests (BEFORE implementing fixes)
  - **Property 2: Preservation** - Existing Functionality
  - **IMPORTANT**: Follow observation-first methodology
  - **GOAL**: Capture baseline behavior that must be preserved after fixes
  - Observe behavior on UNFIXED code for non-buggy inputs:
    - Users with <100 emails sync correctly
    - Plain text emails parse successfully with existing patterns
    - Valid JWT tokens authenticate correctly
    - Transaction queries with valid filters return correct results
    - Analytics for valid date ranges calculate spending accurately
    - OAuth flow with valid credentials creates sessions
    - Scheduled sync with no new emails completes without errors
    - Standard currency formats (Rs., INR) parse correctly
    - CSV export generates valid files
    - Queries with valid sort fields sort correctly
  - Write property-based tests capturing observed behavior patterns
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

---

## Phase 3: Implementation

### Category 1: Critical Security Fixes

- [-] 8. Fix CSRF vulnerability in OAuth flow

  - [x] 8.1 Implement CSRF state store and validation
    - Add in-memory state store with TTL in `backend/app/auth/oauth.py`
    - Implement `validate_and_consume_state()` function
    - Implement `cleanup_expired_states()` function
    - Update `initiate_oauth_flow()` to generate and store state parameter
    - Update `google_callback()` in `backend/app/routes/auth.py` to validate state
    - Add state cleanup scheduler in `backend/main.py`
    - _Bug_Condition: OAuth callback without state validation (isBugCondition where input.oauthCallback AND NOT input.stateValidated)_
    - _Expected_Behavior: State parameter validated, expired/invalid states rejected (expectedBehavior from Property 1)_
    - _Preservation: Valid OAuth flows continue to work (Preservation Requirements 3.3, 3.6)_
    - _Requirements: 1.1, 2.1, 2.2_

  - [ ] 8.2 Verify CSRF exploration test now passes
    - **Property 1: Expected Behavior** - CSRF State Validation
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - Run CSRF attack test from task 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms CSRF protection works)
    - _Requirements: 2.1, 2.2_

  - [ ] 8.3 Verify preservation tests still pass
    - **Property 2: Preservation** - OAuth Flow Preservation
    - **IMPORTANT**: Re-run the SAME tests from task 7 - do NOT write new tests
    - Run OAuth preservation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in valid OAuth flows)


- [ ] 9. Fix JWT exposure in URL

  - [ ] 9.1 Implement HTTPOnly cookie for JWT
    - Update `google_callback()` in `backend/app/routes/auth.py`
    - Set JWT as HTTPOnly cookie on RedirectResponse instead of URL parameter
    - Configure cookie with secure flag for production, samesite=lax
    - Remove JWT from redirect URL
    - _Bug_Condition: JWT token in redirect URL (isBugCondition where input.jwtToken IN input.redirectURL)_
    - _Expected_Behavior: JWT set as HTTPOnly cookie, not in URL (expectedBehavior from Property 2)_
    - _Preservation: Valid JWT authentication continues to work (Preservation Requirements 3.3)_
    - _Requirements: 1.2, 2.3_

  - [ ] 9.2 Verify JWT leakage exploration test now passes
    - **Property 1: Expected Behavior** - JWT HTTPOnly Cookie
    - Re-run JWT leakage test from task 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms JWT not in URL, set as HTTPOnly cookie)
    - _Requirements: 2.3_

  - [ ] 9.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Authentication Preservation
    - Re-run authentication preservation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms authentication still works)

- [ ] 10. Fix production error exposure

  - [ ] 10.1 Implement production error sanitization
    - Add production exception handler in `backend/main.py`
    - Sanitize error messages in production environment
    - Return generic error messages, hide stack traces and internal details
    - Keep detailed errors for development environment
    - _Bug_Condition: Production errors expose internal details (isBugCondition where input.errorResponse CONTAINS stackTrace)_
    - _Expected_Behavior: Errors sanitized in production (expectedBehavior from Property 3)_
    - _Preservation: Development error details preserved (Preservation Requirements)_
    - _Requirements: 1.3, 2.4_

  - [ ] 10.2 Verify error exposure exploration test now passes
    - **Property 1: Expected Behavior** - Error Sanitization
    - Re-run error exposure test from task 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms errors sanitized in production)
    - _Requirements: 2.4_

  - [ ] 10.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Error Handling Preservation
    - Re-run preservation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [-] 11. Fix sort_by field injection vulnerability

  - [x] 11.1 Implement sort field whitelisting
    - Add ALLOWED_SORT_FIELDS whitelist in `backend/app/services/transaction_service.py`
    - Update `get_transactions()` to validate sort_by parameter
    - Raise ValueError for invalid sort fields
    - Include: transaction_date, amount, merchant, bank_name, transaction_type, created_at
    - _Bug_Condition: Arbitrary sort_by parameter accepted (isBugCondition where input.sortByParam NOT IN ALLOWED_FIELDS)_
    - _Expected_Behavior: Only whitelisted fields accepted (expectedBehavior from Property 4)_
    - _Preservation: Valid sort fields continue to work (Preservation Requirements 3.10)_
    - _Requirements: 1.16, 2.17_

  - [ ] 11.2 Verify sort injection exploration test now passes
    - **Property 1: Expected Behavior** - Sort Field Whitelisting
    - Re-run sort injection test from task 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms invalid fields rejected)
    - _Requirements: 2.17_

  - [ ] 11.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Valid Sort Preservation
    - Re-run sort preservation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms valid sort fields still work)

### Category 2: Critical Data Integrity Fixes

- [-] 12. Fix Gmail API pagination data loss

  - [x] 12.1 Implement nextPageToken pagination loop
    - Update `fetch_transaction_emails()` in `backend/app/services/gmail_service.py`
    - Implement pagination loop with nextPageToken
    - Add configurable max_results cap (default 500)
    - Fetch all pages until no nextPageToken or max reached
    - Add logging for page count and total messages
    - _Bug_Condition: Email count >100 without pagination (isBugCondition where input.emailCount > 100 AND NOT input.paginationUsed)_
    - _Expected_Behavior: All emails fetched with pagination (expectedBehavior from Property 5)_
    - _Preservation: Users with <100 emails continue to sync correctly (Preservation Requirements 3.1)_
    - _Requirements: 1.4, 2.5_

  - [ ] 12.2 Verify pagination loss exploration test now passes
    - **Property 1: Expected Behavior** - Gmail Pagination
    - Re-run pagination loss test from task 2
    - **EXPECTED OUTCOME**: Test PASSES (confirms all 150 emails fetched)
    - _Requirements: 2.5_

  - [ ] 12.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Small Volume Sync Preservation
    - Re-run small volume sync tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms <100 email syncs still work)

- [-] 13. Fix incremental sync waste

  - [x] 13.1 Implement incremental sync with last_sync_time
    - Update `sync_user_emails()` in `backend/app/scheduler/sync_job.py`
    - Query last successful sync time from SyncLog
    - Pass last_sync_time to `fetch_transaction_emails()`
    - Update Gmail API query to include after: parameter
    - Add logging for last_sync_time and incremental fetch
    - _Bug_Condition: Scheduled sync fetches all emails (isBugCondition where input.syncType == "scheduled" AND NOT input.lastSyncTimePassed)_
    - _Expected_Behavior: Only new emails fetched (expectedBehavior from Property 6)_
    - _Preservation: First sync and no-new-emails sync continue to work (Preservation Requirements 3.7)_
    - _Requirements: 1.6, 2.7_

  - [ ] 13.2 Verify full sync waste exploration test now passes
    - **Property 1: Expected Behavior** - Incremental Sync
    - Re-run full sync waste test from task 2
    - **EXPECTED OUTCOME**: Test PASSES (confirms only new emails fetched on second sync)
    - _Requirements: 2.7_

  - [ ] 13.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Sync Preservation
    - Re-run sync preservation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms first sync and no-new-emails sync still work)

- [-] 14. Fix concurrent sync data inconsistency

  - [x] 14.1 Implement per-user sync locks and rate limiting
    - Add per-user asyncio.Lock dictionary in `backend/app/scheduler/sync_job.py`
    - Implement `get_user_sync_lock()` function
    - Update `sync_user_emails()` to acquire lock before sync
    - Return early if lock already held
    - Add rate limiting to manual sync endpoint in `backend/app/routes/sync.py` (3/minute)
    - _Bug_Condition: Concurrent syncs without locking (isBugCondition where input.concurrentSyncRequests > 1 AND NOT input.lockAcquired)_
    - _Expected_Behavior: Only one sync per user at a time (expectedBehavior from Property 7)_
    - _Preservation: Single sync requests continue to work (Preservation Requirements)_
    - _Requirements: 1.5, 2.6_

  - [ ] 14.2 Verify concurrent sync exploration test now passes
    - **Property 1: Expected Behavior** - Sync Concurrency Control
    - Re-run concurrent sync test from task 2
    - **EXPECTED OUTCOME**: Test PASSES (confirms only one sync executes, second returns early)
    - _Requirements: 2.6_

  - [ ] 14.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Single Sync Preservation
    - Re-run sync preservation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms single syncs still work)

### Category 3: Event Loop Blocking Fixes

- [ ] 15. Fix Gmail API event loop blocking

  - [ ] 15.1 Implement async wrappers for Gmail API calls
    - Create ThreadPoolExecutor in `backend/app/services/gmail_service.py`
    - Wrap `fetch_transaction_emails()` synchronous logic with run_in_executor()
    - Wrap `get_email_content()` synchronous logic with run_in_executor()
    - Ensure all Gmail API calls execute in thread pool
    - Add async/await throughout call chain
    - _Bug_Condition: Gmail API calls block event loop (isBugCondition where input.gmailAPICall AND input.executionContext == "eventLoop")_
    - _Expected_Behavior: Gmail API calls don't block event loop (expectedBehavior from Property 8)_
    - _Preservation: Email fetching results unchanged (Preservation Requirements 3.1, 3.2)_
    - _Requirements: 1.7, 2.8_

  - [ ] 15.2 Verify event loop blocking exploration test now passes
    - **Property 1: Expected Behavior** - Async Gmail API Calls
    - Re-run event loop blocking test from task 3
    - **EXPECTED OUTCOME**: Test PASSES (confirms event loop not blocked, latency <10ms)
    - _Requirements: 2.8_

  - [ ] 15.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Email Fetching Preservation
    - Re-run email fetching preservation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms email fetching results unchanged)


- [ ] 16. Fix token refresh event loop blocking

  - [ ] 16.1 Implement async wrapper for token refresh
    - Create `refresh_access_token_async()` in `backend/app/auth/oauth.py`
    - Wrap synchronous `refresh_access_token()` with run_in_executor()
    - Update `sync_user_emails()` to use async version
    - Ensure token refresh doesn't block event loop
    - _Bug_Condition: Token refresh blocks event loop (isBugCondition where input.tokenRefresh AND input.executionContext == "eventLoop")_
    - _Expected_Behavior: Token refresh doesn't block event loop (expectedBehavior from Property 9)_
    - _Preservation: Token refresh results unchanged (Preservation Requirements 3.3)_
    - _Requirements: 1.8, 2.9_

  - [ ] 16.2 Verify token refresh blocking exploration test now passes
    - **Property 1: Expected Behavior** - Async Token Refresh
    - Re-run token refresh blocking test from task 3
    - **EXPECTED OUTCOME**: Test PASSES (confirms event loop not blocked during refresh)
    - _Requirements: 2.9_

  - [ ] 16.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Token Refresh Preservation
    - Re-run token refresh preservation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms token refresh results unchanged)

### Category 4: Parsing Enhancements

- [-] 17. Fix HTML email parsing failure

  - [x] 17.1 Implement BeautifulSoup HTML stripping
    - Add beautifulsoup4 and lxml to `backend/requirements.txt`
    - Update `_strip_html()` in `backend/app/services/email_parser.py` to use BeautifulSoup
    - Decode HTML entities, strip tags, clean up whitespace
    - Update `_extract_body()` in `backend/app/services/gmail_service.py` to prioritize text/plain
    - Strip HTML from HTML parts when plain text not available
    - _Bug_Condition: HTML emails fail to parse (isBugCondition where input.emailFormat == "HTML" AND NOT input.htmlStripped)_
    - _Expected_Behavior: HTML emails parsed successfully (expectedBehavior from Property 10)_
    - _Preservation: Plain text emails continue to parse (Preservation Requirements 3.2)_
    - _Requirements: 1.9, 1.11, 2.10, 2.12_

  - [ ] 17.2 Verify HTML parsing exploration test now passes
    - **Property 1: Expected Behavior** - HTML Email Parsing
    - Re-run HTML parsing test from task 4
    - **EXPECTED OUTCOME**: Test PASSES (confirms HTML emails parsed, tags stripped)
    - _Requirements: 2.10, 2.12_

  - [ ] 17.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Plain Text Parsing Preservation
    - Re-run plain text parsing tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms plain text emails still parse correctly)

- [-] 18. Fix ₹ symbol amount extraction failure

  - [x] 18.1 Add Unicode currency symbol support
    - Update AMOUNT_PATTERNS in `backend/app/services/email_parser.py`
    - Add ₹ Unicode symbol to all amount patterns
    - Add patterns for Indian currency formats
    - Test with various ₹ formats: "₹1,234.56", "₹ 500", "debited ₹100"
    - _Bug_Condition: ₹ symbol amounts not extracted (isBugCondition where input.currencySymbol == "₹" AND NOT input.amountExtracted)_
    - _Expected_Behavior: ₹ amounts extracted successfully (expectedBehavior from Property 11)_
    - _Preservation: Rs. and INR amounts continue to parse (Preservation Requirements 3.8)_
    - _Requirements: 1.10, 2.11_

  - [ ] 18.2 Verify ₹ symbol exploration test now passes
    - **Property 1: Expected Behavior** - Unicode Currency Support
    - Re-run ₹ symbol test from task 4
    - **EXPECTED OUTCOME**: Test PASSES (confirms ₹ amounts extracted)
    - _Requirements: 2.11_

  - [ ] 18.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Standard Currency Preservation
    - Re-run standard currency parsing tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms Rs. and INR still parse correctly)

### Category 5: Feature Additions

- [-] 19. Add new transaction fields (category, payment_method, upi_reference, raw_snippet)

  - [x] 19.1 Create database migration for new fields
    - Create Alembic migration `add_transaction_fields.py`
    - Add category (String(100), nullable, indexed)
    - Add payment_method (String(50), nullable)
    - Add upi_reference (String(255), nullable, indexed)
    - Add raw_snippet (String(500), nullable)
    - Test upgrade and downgrade
    - _Bug_Condition: Transaction fields missing (isBugCondition where input.transactionCreated AND input.categoryField == NULL)_
    - _Expected_Behavior: New fields available in database (expectedBehavior from Property 13)_
    - _Preservation: Existing transactions unaffected (Preservation Requirements 3.4)_
    - _Requirements: 1.12, 2.13_

  - [x] 19.2 Update Transaction model with new fields
    - Add new columns to Transaction model in `backend/app/models/transaction.py`
    - Update ParsedTransaction schema in `backend/app/services/email_parser.py`
    - Update `create_transaction()` in `backend/app/services/transaction_service.py` to store new fields
    - Update transaction response schemas to include new fields
    - _Requirements: 1.12, 2.13_

  - [ ] 19.3 Verify missing fields exploration test now passes
    - **Property 1: Expected Behavior** - Extended Transaction Fields
    - Re-run missing fields test from task 5
    - **EXPECTED OUTCOME**: Test PASSES (confirms new fields stored in database)
    - _Requirements: 2.13_

  - [ ] 19.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Transaction Query Preservation
    - Re-run transaction query tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms existing queries still work)

- [ ] 20. Add UPI reference and payment method extraction

  - [x] 20.1 Implement UPI and payment method extraction
    - Add UPI_PATTERNS to `backend/app/services/email_parser.py`
    - Add PAYMENT_METHOD_KEYWORDS dictionary
    - Implement `extract_upi_reference()` function
    - Implement `extract_payment_method()` function
    - Update `parse_email()` to extract UPI and payment method
    - _Bug_Condition: UPI not extracted (isBugCondition where input.emailHasUPI AND NOT input.upiExtracted)_
    - _Expected_Behavior: UPI and payment method extracted (expectedBehavior from Property 14)_
    - _Preservation: Existing parsing unchanged (Preservation Requirements 3.2)_
    - _Requirements: 1.13, 2.14_

  - [ ] 20.2 Verify UPI extraction exploration test now passes
    - **Property 1: Expected Behavior** - UPI and Payment Method Extraction
    - Re-run UPI extraction test from task 5
    - **EXPECTED OUTCOME**: Test PASSES (confirms UPI references extracted)
    - _Requirements: 2.14_

  - [ ] 20.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Parsing Preservation
    - Re-run parsing preservation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms existing parsing still works)

- [ ] 21. Add auto-categorization engine

  - [x] 21.1 Implement keyword-based categorization
    - Add CATEGORY_KEYWORDS dictionary in `backend/app/services/email_parser.py`
    - Implement `fuzzy_match()` function using SequenceMatcher
    - Implement `auto_categorize()` function with exact and fuzzy matching
    - Support categories: Food, Groceries, Shopping, Transport, Bills, Entertainment, Healthcare, Education
    - Update `parse_email()` to auto-categorize transactions
    - _Bug_Condition: No auto-categorization (isBugCondition where input.transactionCreated AND NOT input.autoCategorized)_
    - _Expected_Behavior: Transactions auto-categorized (expectedBehavior from Property 15)_
    - _Preservation: Manual categorization still possible (Preservation Requirements)_
    - _Requirements: 1.14, 2.15_

  - [ ] 21.2 Verify categorization exploration test now passes
    - **Property 1: Expected Behavior** - Auto-Categorization
    - Re-run categorization test from task 5
    - **EXPECTED OUTCOME**: Test PASSES (confirms "Swiggy" categorized as "Food")
    - _Requirements: 2.15_

  - [ ] 21.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Transaction Creation Preservation
    - Re-run transaction creation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms transaction creation still works)

- [ ] 22. Add merchant name normalization in analytics

  - [x] 22.1 Implement case-insensitive merchant grouping
    - Update `get_category_breakdown()` in `backend/app/services/analytics_service.py`
    - Use func.lower() for GROUP BY merchant
    - Capitalize merchant names in output for display
    - Test with "AMAZON", "Amazon", "amazon" - should group as one
    - _Bug_Condition: Case-sensitive merchant grouping (isBugCondition where input.merchantGrouping AND input.caseSensitive)_
    - _Expected_Behavior: Merchants normalized (expectedBehavior from Property 16)_
    - _Preservation: Analytics calculations unchanged (Preservation Requirements 3.5)_
    - _Requirements: 1.15, 2.16_

  - [ ] 22.2 Verify merchant case sensitivity exploration test now passes
    - **Property 1: Expected Behavior** - Merchant Normalization
    - Re-run merchant case test from task 5
    - **EXPECTED OUTCOME**: Test PASSES (confirms "AMAZON" and "amazon" grouped together)
    - _Requirements: 2.16_

  - [ ] 22.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Analytics Preservation
    - Re-run analytics preservation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms analytics calculations still accurate)

### Category 6: Code Quality Fixes

- [ ] 23. Replace print() with structured logging

  - [ ] 23.1 Implement structured logging in auth routes
    - Replace all print() statements in `backend/app/routes/auth.py` with structlog logger
    - Use logger.info(), logger.error(), logger.warning() with structured fields
    - Add context fields: user_id, error_type, event_name
    - Ensure logs are queryable in production
    - _Bug_Condition: print() used for logging (isBugCondition where input.authEvent AND input.logMethod == "print")_
    - _Expected_Behavior: Structured logging used (expectedBehavior from Property 17)_
    - _Preservation: Log information preserved (Preservation Requirements)_
    - _Requirements: 1.17, 2.18_

  - [ ] 23.2 Verify print logging exploration test now passes
    - **Property 1: Expected Behavior** - Structured Logging
    - Re-run print logging test from task 6
    - **EXPECTED OUTCOME**: Test PASSES (confirms structlog used instead of print)
    - _Requirements: 2.18_

  - [ ] 23.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Auth Flow Preservation
    - Re-run auth flow tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms auth flow still works)


- [ ] 24. Fix SQLAlchemy 2.0 raw SQL compatibility

  - [ ] 24.1 Wrap raw SQL with text() in tests
    - Update `backend/tests/conftest.py` to import text from sqlalchemy
    - Wrap all raw SQL strings with text() wrapper
    - Replace: `db.execute("DELETE FROM transactions")`
    - With: `db.execute(text("DELETE FROM transactions"))`
    - Test all test files for SQLAlchemy 2.0 compatibility
    - _Bug_Condition: Raw SQL not wrapped (isBugCondition where input.testSQL AND NOT input.textWrapped)_
    - _Expected_Behavior: Raw SQL wrapped with text() (expectedBehavior from Property 18)_
    - _Preservation: Test behavior unchanged (Preservation Requirements)_
    - _Requirements: 1.18, 2.19_

  - [ ] 24.2 Verify raw SQL exploration test now passes
    - **Property 1: Expected Behavior** - SQLAlchemy 2.0 Compatibility
    - Re-run raw SQL test from task 6
    - **EXPECTED OUTCOME**: Test PASSES (confirms raw SQL works with text() wrapper)
    - _Requirements: 2.19_

  - [ ] 24.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Test Behavior Preservation
    - Re-run all tests to confirm behavior unchanged
    - **EXPECTED OUTCOME**: Tests PASS (confirms test results unchanged)

- [ ] 25. Add SQLAlchemy ORM relationships

  - [x] 25.1 Define relationships in models
    - Add relationship() to User model in `backend/app/models/user.py`
    - Add transactions and sync_logs relationships with back_populates
    - Add relationship() to Transaction model in `backend/app/models/transaction.py`
    - Add user relationship with back_populates
    - Add relationship() to SyncLog model in `backend/app/models/sync_log.py`
    - Add user relationship with back_populates
    - Configure cascade="all, delete-orphan" for parent relationships
    - _Bug_Condition: Relationships not defined (isBugCondition where input.modelQuery AND NOT input.relationshipDefined)_
    - _Expected_Behavior: Relationships enable ORM navigation (expectedBehavior from Property 19)_
    - _Preservation: Existing queries unchanged (Preservation Requirements 3.4)_
    - _Requirements: 1.19, 2.20_

  - [ ] 25.2 Verify relationship exploration test now passes
    - **Property 1: Expected Behavior** - ORM Relationships
    - Re-run relationship test from task 6
    - **EXPECTED OUTCOME**: Test PASSES (confirms user.transactions works)
    - _Requirements: 2.20_

  - [ ] 25.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Query Preservation
    - Re-run query tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms existing queries still work)

- [ ] 26. Add updated_at timestamp tracking for User model

  - [x] 26.1 Create migration and add updated_at field
    - Create Alembic migration `add_user_updated_at.py`
    - Add updated_at column (DateTime with timezone, default CURRENT_TIMESTAMP)
    - Configure onupdate to automatically update timestamp
    - Test upgrade and downgrade
    - Update User model in `backend/app/models/user.py` with updated_at field
    - _Bug_Condition: updated_at not tracked (isBugCondition where input.userUpdated AND NOT input.updatedAtSet)_
    - _Expected_Behavior: updated_at automatically updated (expectedBehavior from Property 20)_
    - _Preservation: Existing user operations unchanged (Preservation Requirements)_
    - _Requirements: 1.20, 2.21_

  - [ ] 26.2 Verify updated_at exploration test now passes
    - **Property 1: Expected Behavior** - User Updated Timestamp
    - Re-run updated_at test from task 6
    - **EXPECTED OUTCOME**: Test PASSES (confirms updated_at changes on user update)
    - _Requirements: 2.21_

  - [ ] 26.3 Verify preservation tests still pass
    - **Property 2: Preservation** - User Operations Preservation
    - Re-run user operation tests from task 7
    - **EXPECTED OUTCOME**: Tests PASS (confirms user operations still work)

---

## Phase 4: Final Verification

- [ ] 27. Run comprehensive test suite
  - Run all exploration tests - verify they now PASS (previously failed on unfixed code)
  - Run all preservation tests - verify they still PASS (behavior unchanged for non-buggy inputs)
  - Run unit tests for all 20+ fixes
  - Run integration tests for end-to-end flows
  - Verify all tests pass

- [ ] 28. Run database migrations
  - Generate Alembic migration for transaction fields
  - Generate Alembic migration for user updated_at
  - Test upgrade migrations on test database
  - Test downgrade migrations
  - Verify data integrity after migrations

- [ ] 29. Performance validation
  - Measure event loop latency during Gmail API calls (should be <10ms)
  - Measure sync time for 100 vs 500 emails (should scale linearly)
  - Measure API quota usage with incremental sync (should reduce by 90%+)
  - Measure categorization performance (should be <1ms per transaction)
  - Verify all performance targets met

- [ ] 30. Security validation
  - Test CSRF protection with various attack vectors
  - Verify JWT not in browser history or logs
  - Test production error sanitization
  - Test sort_by injection attempts
  - Verify all security fixes effective

- [ ] 31. Final checkpoint - Ensure all tests pass
  - Confirm all 20+ bugs fixed
  - Confirm all preservation tests pass
  - Confirm no regressions introduced
  - Ask user if questions arise or additional testing needed

---

## Dependencies and Execution Order

### Critical Path
1. Tasks 1-6: Exploration tests (can run in parallel, all BEFORE fixes)
2. Task 7: Preservation tests (BEFORE fixes)
3. Tasks 8-26: Implementation (can be parallelized by category, but each task's sub-tasks must be sequential)
4. Tasks 27-31: Final verification (sequential)

### Category Dependencies
- Security fixes (8-11): Independent, can be done in parallel
- Data integrity fixes (12-14): Task 13 depends on 12 (incremental sync needs pagination)
- Performance fixes (15-16): Independent, can be done in parallel
- Parsing fixes (17-18): Independent, can be done in parallel
- Feature additions (19-22): Task 20-22 depend on 19 (need new fields in database)
- Code quality fixes (23-26): Independent, can be done in parallel

### Testing Dependencies
- All exploration tests (1-6) must run BEFORE any implementation
- Preservation tests (7) must run BEFORE any implementation
- Each implementation task includes verification sub-tasks that re-run exploration and preservation tests
- Final verification (27-31) must run AFTER all implementation tasks

---

## File Modification Summary

### Modified Files (15)
1. `backend/app/auth/oauth.py` - CSRF state store, async token refresh
2. `backend/app/routes/auth.py` - State validation, HTTPOnly cookie, structured logging
3. `backend/main.py` - Production error handler, state cleanup scheduler
4. `backend/app/services/transaction_service.py` - Sort field whitelist, new field handling
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

### New Files (2)
1. `backend/alembic/versions/YYYYMMDD_add_transaction_fields.py` - Migration for transaction fields
2. `backend/alembic/versions/YYYYMMDD_add_user_updated_at.py` - Migration for user updated_at

### New Test Files (6)
1. `backend/tests/test_security_bugs.py` - Security exploration tests (task 1)
2. `backend/tests/test_data_loss_bugs.py` - Data loss exploration tests (task 2-3)
3. `backend/tests/test_parsing_bugs.py` - Parsing exploration tests (task 4)
4. `backend/tests/test_feature_bugs.py` - Feature exploration tests (task 5)
5. `backend/tests/test_quality_bugs.py` - Quality exploration tests (task 6)
6. `backend/tests/test_preservation.py` - Preservation tests (task 7)

---

## Notes

- All exploration tests (tasks 1-6) MUST be written and run on UNFIXED code BEFORE implementing any fixes
- Exploration tests are EXPECTED to FAIL on unfixed code - this confirms the bugs exist
- Preservation tests (task 7) MUST be written and run on UNFIXED code to capture baseline behavior
- Preservation tests are EXPECTED to PASS on unfixed code - this confirms what to preserve
- Each implementation task includes verification sub-tasks that re-run the relevant exploration and preservation tests
- After fixes, exploration tests should PASS (bug fixed) and preservation tests should still PASS (no regressions)
- Use property-based testing for preservation tests to generate many test cases automatically
- The bugfix workflow ensures systematic validation: explore → preserve → implement → verify
- All 20+ fixes are independently testable and can be implemented in parallel within their categories
- Database migrations must be tested for both upgrade and downgrade paths
- Performance validation ensures fixes don't degrade system performance
- Security validation ensures all attack vectors are blocked
