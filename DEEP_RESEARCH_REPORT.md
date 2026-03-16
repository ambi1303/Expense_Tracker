# Expense Tracker – Deep Research Report

**Date:** March 16, 2025  
**Scope:** Full codebase analysis for bugs, security, improvements

---

## Executive Summary

This report identifies **critical bugs**, **security vulnerabilities**, **code quality issues**, and **areas for improvement** in the Expense Tracker application. The highest-priority items are a security-critical unvalidated session endpoint, broken pagination, and an OAuth flow mismatch with the documented fix.

---

## 1. Critical Bugs

### 1.1 Pagination Broken on Transactions Page
**Severity:** Critical  
**Files:** `frontend/src/pages/Transactions.tsx` (lines 28–31)

**Problem:** The backend expects `skip` and `limit` for pagination, but the frontend sends `page` and `limit`:

```tsx
// Frontend sends:
const params = { page: currentPage, limit: 20 };

// Backend expects (transactions.py:34-35):
skip: int = Query(0, ge=0)
limit: int = Query(50, ge=1, le=100)
```

**Impact:** All pages show the first 20 records. Clicking "Next" does nothing because `skip` remains 0.

**Fix:**
```tsx
const params: any = {
  skip: (currentPage - 1) * 20,
  limit: 20,
};
```

---

### 1.2 Filter Parameter Mismatch in applyFilters
**Severity:** High  
**Files:** `frontend/src/pages/Transactions.tsx` (lines 56–61)

**Problem:** `applyFilters` builds URL params with `type`, but the API and `fetchTransactions` use `transaction_type`:

```tsx
// applyFilters uses:
if (filters.type) params.type = filters.type;  // Wrong

// fetchTransactions and API expect:
if (filters.type) params.transaction_type = filters.type;  // Correct
```

**Impact:** Filter by transaction type in the URL is lost when applying filters; the backend never receives `transaction_type`.

**Fix:** Use `transaction_type` in `applyFilters` and `handlePageChange`:
```tsx
if (filters.type) params.transaction_type = filters.type;
```

---

### 1.3 OAuth Callback vs. Documented Flow Mismatch
**Severity:** High  
**Files:** `backend/app/routes/auth.py` (lines 161–162), `COOKIE_FIX_APPLIED.md`

**Problem:** The fix document says the callback should redirect to `/auth/complete?token=...`, but the code redirects to `/dashboard` and sets the cookie on the redirect:

```python
# Actual code (auth.py:161-162):
redirect_response = RedirectResponse(url=f"{frontend_url}/dashboard")

# Documented flow (COOKIE_FIX_APPLIED.md):
# "Redirects to frontend with token in URL: `/auth/complete?token=...`"
```

**Impact:** If cookies are lost on cross-origin redirect (the original problem described in the doc), users land on the dashboard without a session. The `AuthComplete` page and `set-session` flow are never used because the callback never sends the token.

**Fix:** Align implementation with the documented fix:
```python
redirect_response = RedirectResponse(
    url=f"{frontend_url}/auth/complete?token={session_token}"
)
# Do NOT set cookie on this redirect (cross-origin won't persist)
```

---

### 1.4 Double Filter Effect on Transactions Page
**Severity:** Medium  
**Files:** `frontend/src/pages/Transactions.tsx` (lines 84–88)

**Problem:** The `useEffect` that calls `applyFilters` runs on every `filters` change. That updates `searchParams`, which triggers `fetchTransactions`. The effect also runs on initial mount before the user has changed anything, so:

1. User loads page → `applyFilters()` runs → URL becomes `?page=1` → fetch runs  
2. User types in merchant → after 500ms `applyFilters()` runs → URL updates → fetch runs  
3. Possible race between filter updates and URL/param updates

**Impact:** Extra network requests, potential flicker, and confusing behavior when filters are partially filled.

**Suggestion:** Debounce only on user-initiated filter changes; avoid applying filters on initial mount if they are already in sync with the URL.

---

## 2. Security Vulnerabilities

### 2.1 Unvalidated set-session Endpoint
**Severity:** Critical  
**Files:** `backend/app/routes/auth.py` (lines 28–59)

**Problem:** `/auth/set-session` accepts any string as `token` and sets it as the session cookie without validating the JWT:

```python
@router.post("/set-session")
async def set_session_cookie(token: str, response: Response):
    response.set_cookie(key="session_token", value=token, ...)
    return {"success": True}
```

**Impact:** An attacker can:
- Call `POST /auth/set-session?token=<forged_or_stolen_jwt>` to impersonate any user
- Set an arbitrary value as the session cookie

**Fix:** Validate the token before setting the cookie:
```python
from app.auth.jwt_handler import verify_session_token

@router.post("/set-session")
async def set_session_cookie(token: str, response: Response):
    try:
        verify_session_token(token)  # Raises if invalid
    except (JWTError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid token")
    response.set_cookie(...)
```

---

### 2.2 Debug Endpoint Exposes Internal Information
**Severity:** High  
**Files:** `backend/main.py` (lines 163–208)

**Problem:** `GET /debug/db` is unauthenticated and returns:
- Database name
- Table list
- User count
- Database host/URL
- Raw exception strings on error

**Impact:** Information disclosure and potential reconnaissance for attackers.

**Fix:**
- Disable in production or guard with `ENABLE_DEBUG_API=false`
- Avoid exposing database URL and exception details
- Add authentication or IP allowlist if the endpoint must exist

---

### 2.3 JWT Error Message Leakage
**Severity:** Medium  
**Files:** `backend/app/auth/middleware.py` (lines 58–62)

**Problem:** JWT validation errors expose library-specific messages:
```python
detail=f"Invalid or expired token: {str(e)}"
```

**Fix:** Use a generic message in production:
```python
detail="Invalid or expired token"
```

---

### 2.4 Sync Error Exposure
**Severity:** Medium  
**Files:** `backend/app/routes/sync.py` (lines 129–136)

**Problem:** Sync failures return the full exception string in the response, which can leak internal details.

**Fix:** Return a generic message in production and log the full error server-side.

---

### 2.5 SQL-Like Injection Risk in Filters
**Severity:** Low (mitigated by Pydantic)  
**Files:** `backend/app/services/transaction_service.py` (lines 206–209)

**Problem:** User input is interpolated into `ilike`:
```python
query = query.where(Transaction.merchant.ilike(f"%{filters.merchant}%"))
```

**Mitigation:** FastAPI/Pydantic validation. Risk increases if filters are ever sourced from unsanitized input.

**Recommendation:** Use SQLAlchemy bind parameters or ensure all filter inputs are strictly validated.

---

## 3. Code Quality Issues

### 3.1 Rate Limiter Not Wired
**Severity:** High  
**Files:** `backend/app/routes/sync.py`, `backend/main.py`

**Problem:** The sync route uses `@limiter.limit("3/minute")` but SlowAPI’s limiter is not registered with the FastAPI app. The rate limit is not enforced.

**Fix:** In `main.py`:
```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter  # from sync router or shared
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

---

### 3.2 Typo in main.py
**Severity:** Low  
**Files:** `backend/main.py` (lines 14–15)

```python
elif os.path.exists(".evn"):
    load_dotenv(".evn")
```

**Fix:** Use `.env` (or remove if `.env` is always used).

---

### 3.3 Logout Cookie May Not Clear
**Severity:** Medium  
**Files:** `backend/app/routes/auth.py` (lines 234–239)

**Problem:** `delete_cookie` does not specify `path="/"`, but the cookie was set with `path="/"`. Some browsers may not clear it.

**Fix:**
```python
response.delete_cookie(
    key="session_token",
    path="/",
    httponly=True,
    secure=...,
    samesite="lax"
)
```

---

### 3.4 Duplicated Loading Spinner
**Severity:** Low  
**Files:** `AuthComplete.tsx`, `Dashboard.tsx`, `Transactions.tsx`, `SyncButton.tsx`, `ExportButton.tsx`

**Fix:** Extract a shared `LoadingSpinner` component.

---

### 3.5 Silent Error Handling
**Severity:** Medium  
**Files:** `frontend/src/context/AuthContext.tsx`, `frontend/src/components/dashboard/ExportButton.tsx`

**Problem:**
- `checkAuth` catches errors and sets `user=null` with no logging or user feedback
- Export failures are only `console.error`’d; the user is not informed
- Logout failure redirects anyway; user may still have a valid session

**Fix:** Add user-visible error states and/or toasts for failures.

---

## 4. Architecture & Scalability

### 4.1 OAuth State in Process Memory
**Files:** `backend/app/auth/oauth.py` (lines 29–31)

**Problem:** `_oauth_state_store` is an in-memory dict. With multiple workers or instances, state is not shared and OAuth flows can fail.

**Fix:** Use Redis or another shared store for OAuth state.

---

### 4.2 Per-User Sync Lock Dictionary Growth
**Files:** `backend/app/scheduler/sync_job.py` (lines 30–31, 44–47)

**Problem:** `_user_sync_locks` grows with each new user and is never cleaned. Long-lived processes will accumulate locks.

**Fix:** Use LRU or TTL-based cleanup, or a bounded cache.

---

## 5. UX/UI Improvements

### 5.1 Hardcoded Currency Symbol
**Files:** `frontend/src/components/transactions/TransactionTable.tsx`, `frontend/src/components/dashboard/SummaryCards.tsx`, `CategoryBreakdown.tsx`

**Problem:** Rupee symbol `₹` is hardcoded while the model supports INR, USD, EUR, GBP.

**Fix:** Use a currency map or `Intl.NumberFormat` with the transaction’s currency.

---

### 5.2 Missing User Feedback
- Export failure: no visible error
- Sync success/error message disappears after 5 seconds
- Settings: sync history errors only logged

**Fix:** Add toasts or inline error messages with clear actions.

---

### 5.3 Accessibility
- Loading spinners lack `aria-busy` / `aria-live`
- Table headers missing `scope`
- Form controls could use clearer `aria-label`s

---

## 6. Configuration & Environment

### 6.1 Hardcoded API Base URL
**Files:** `frontend/src/services/api.ts` (line 4)

```ts
baseURL: 'http://localhost:8000',
```

**Fix:** Use `import.meta.env.VITE_API_URL || 'http://localhost:8000'`.

---

### 6.2 Hardcoded CORS Origins
**Files:** `backend/main.py` (lines 99–105)

**Fix:** Read allowed origins from environment (e.g. `CORS_ORIGINS`).

---

## 7. Priority Fix Matrix

| Priority | Issue | Location | Effort |
|----------|-------|----------|--------|
| P0 | set-session accepts any token | `auth.py:28-59` | Low |
| P0 | Pagination broken (page vs skip) | `Transactions.tsx:28-31` | Low |
| P1 | OAuth callback vs documented flow | `auth.py:161-162` | Medium |
| P1 | Debug endpoint exposed | `main.py:163-208` | Low |
| P1 | Rate limiter not wired | `main.py`, `sync.py` | Low |
| P1 | Logout cookie path | `auth.py:234-239` | Low |
| P2 | Filter param mismatch | `Transactions.tsx:56-60` | Low |
| P2 | JWT/sync error leakage | `middleware.py`, `sync.py` | Low |
| P2 | Currency symbol | Multiple components | Medium |
| P3 | .evn typo | `main.py:14-15` | Trivial |
| P3 | Extracted LoadingSpinner | Multiple | Low |

---

## 8. Recommended Next Steps

1. **Immediate:** Fix set-session validation and pagination.
2. **Short-term:** Align OAuth callback with the documented cookie fix and wire the rate limiter.
3. **Medium-term:** Guard or remove the debug endpoint, fix logout cookie path, and improve error UX.
4. **Long-term:** Introduce shared OAuth state storage, cleanup for sync locks, and dynamic currency display.

---

*Report generated from codebase analysis. Re-verify in your environment before applying changes.*
