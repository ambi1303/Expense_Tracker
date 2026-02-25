# Bugfix Requirements Document

## Introduction

The Gmail Expense Tracker backend contains multiple critical vulnerabilities and defects across security, data integrity, and code quality that must be systematically fixed before production deployment. These issues span 20+ areas including CSRF vulnerabilities in OAuth flow, JWT exposure in URLs, data loss from missing pagination, event loop blocking, HTML parsing failures, missing currency support, and various code quality problems. This bugfix addresses all identified issues to ensure a secure, reliable, and production-ready backend.

## Bug Analysis

### Current Behavior (Defect)

#### Security Vulnerabilities (Critical)

1.1 WHEN OAuth callback is received THEN the system does not verify the state parameter, making it vulnerable to CSRF attacks

1.2 WHEN OAuth authentication completes THEN the system exposes JWT token in redirect URL, leaking it to browser history, logs, and Referer headers

1.3 WHEN production errors occur THEN the system exposes internal error details to users, revealing implementation details

#### Data Loss Issues (Critical)

1.4 WHEN a user has more than 100 bank emails THEN the system only fetches the first 100 emails, losing transaction data

1.5 WHEN manual sync is triggered multiple times concurrently THEN the system processes duplicate syncs without locking, causing data inconsistencies

1.6 WHEN scheduled sync runs THEN the system fetches ALL emails instead of only new ones since last sync, wasting resources and time

#### Event Loop Blocking (Critical)

1.7 WHEN Gmail API calls are made THEN the system uses synchronous calls that block the FastAPI event loop, degrading performance

1.8 WHEN OAuth token refresh is needed during sync THEN the system uses synchronous refresh that blocks the event loop

#### Parsing Failures (High Priority)

1.9 WHEN bank emails are HTML-formatted THEN the system fails to parse them because it only handles plain text

1.10 WHEN bank emails contain ₹ symbol THEN the system fails to extract amounts because patterns don't include Unicode currency symbols

1.11 WHEN email body contains both plain text and HTML THEN the system may extract HTML tags instead of clean text

#### Missing Functionality (High Priority)

1.12 WHEN transactions are stored THEN the system does not capture category, payment_method, upi_reference, or raw_snippet fields

1.13 WHEN transactions are parsed THEN the system does not extract UPI IDs or payment methods from email content

1.14 WHEN transactions are created THEN the system does not auto-categorize them, requiring manual categorization

1.15 WHEN analytics group by merchant THEN the system treats "AMAZON", "Amazon", and "amazon" as separate merchants due to case sensitivity

#### Security & Quality Issues (Medium Priority)

1.16 WHEN sort_by parameter is provided to transaction queries THEN the system accepts any string without validation, potentially exposing internal fields

1.17 WHEN authentication events occur THEN the system uses print() statements instead of structured logging

1.18 WHEN tests run with raw SQL THEN the system fails with SQLAlchemy 2.0 because SQL strings are not wrapped with text()

1.19 WHEN ORM models are defined THEN the system lacks relationship() definitions, preventing efficient ORM navigation

1.20 WHEN user records are modified THEN the system does not track updated_at timestamp

### Expected Behavior (Correct)

#### Security Fixes (Critical)

2.1 WHEN OAuth flow is initiated THEN the system SHALL generate a unique state parameter, store it server-side with TTL, and return it to the client

2.2 WHEN OAuth callback is received THEN the system SHALL verify the state parameter matches stored value, reject mismatches, and clean up used states

2.3 WHEN OAuth authentication completes THEN the system SHALL set JWT as HTTPOnly cookie directly on RedirectResponse instead of URL parameter

2.4 WHEN production errors occur THEN the system SHALL sanitize error messages to hide internal implementation details

#### Data Integrity Fixes (Critical)

2.5 WHEN fetching emails from Gmail API THEN the system SHALL implement nextPageToken pagination loop with configurable max cap to fetch all emails

2.6 WHEN manual sync is triggered THEN the system SHALL use per-user asyncio.Lock to prevent concurrent syncs and add rate limiting

2.7 WHEN scheduled sync runs THEN the system SHALL query last successful sync time and pass it to Gmail API to fetch only new emails

#### Async/Performance Fixes (Critical)

2.8 WHEN Gmail API calls are made THEN the system SHALL wrap all synchronous Gmail API calls with run_in_executor() to avoid blocking

2.9 WHEN OAuth token refresh is needed THEN the system SHALL wrap refresh_access_token() with run_in_executor() for async execution

#### Parsing Enhancements (High Priority)

2.10 WHEN HTML-formatted emails are received THEN the system SHALL use BeautifulSoup to strip HTML tags before regex operations

2.11 WHEN extracting amounts from emails THEN the system SHALL update AMOUNT_PATTERNS to include ₹ Unicode symbol and other Indian currency formats

2.12 WHEN extracting email body THEN the system SHALL prefer text/plain content over HTML when both are available

#### Feature Additions (High Priority)

2.13 WHEN storing transactions THEN the system SHALL add category, payment_method, upi_reference, and raw_snippet fields to Transaction model with Alembic migration

2.14 WHEN parsing emails THEN the system SHALL extract UPI IDs using UPI_PATTERNS and payment methods using extract_payment_method() function

2.15 WHEN transactions are created THEN the system SHALL auto-categorize them using keyword-based categorization engine with fuzzy matching for Food, Groceries, Shopping, Transport, Bills, etc.

2.16 WHEN analytics group by merchant THEN the system SHALL use func.lower() for grouping and capitalize output to normalize merchant names

#### Code Quality Fixes (Medium Priority)

2.17 WHEN transaction queries use sort_by parameter THEN the system SHALL validate against ALLOWED_SORT_FIELDS whitelist

2.18 WHEN authentication events occur THEN the system SHALL use structlog logger instead of print() statements

2.19 WHEN tests execute raw SQL THEN the system SHALL wrap SQL strings with text() wrapper for SQLAlchemy 2.0 compatibility

2.20 WHEN ORM models are defined THEN the system SHALL add relationship() definitions for User, Transaction, and SyncLog models

2.21 WHEN user records are modified THEN the system SHALL automatically update updated_at timestamp

### Unchanged Behavior (Regression Prevention)

3.1 WHEN users with fewer than 100 emails sync THEN the system SHALL CONTINUE TO fetch and process all their emails correctly

3.2 WHEN plain text bank emails are received THEN the system SHALL CONTINUE TO parse them successfully with existing regex patterns

3.3 WHEN valid JWT tokens are provided THEN the system SHALL CONTINUE TO authenticate users correctly

3.4 WHEN transactions are queried with valid filters THEN the system SHALL CONTINUE TO return correct filtered results

3.5 WHEN analytics are requested for valid date ranges THEN the system SHALL CONTINUE TO calculate spending trends accurately

3.6 WHEN OAuth flow completes successfully with valid credentials THEN the system SHALL CONTINUE TO create user sessions and store tokens

3.7 WHEN scheduled sync runs for users with no new emails THEN the system SHALL CONTINUE TO complete successfully without errors

3.8 WHEN transaction amounts are extracted from standard formats (Rs., INR) THEN the system SHALL CONTINUE TO parse them correctly

3.9 WHEN CSV export is requested THEN the system SHALL CONTINUE TO generate valid CSV files with existing fields

3.10 WHEN database queries use existing sort fields (date, amount, merchant) THEN the system SHALL CONTINUE TO sort results correctly
