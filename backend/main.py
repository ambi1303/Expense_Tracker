"""
Gmail AI Expense Tracker - Main Application Entry Point
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import structlog

# Load environment variables from .env file
if os.path.exists(".env"):
    load_dotenv(".env")

# Import routers
from app.routes import auth
from app.routes import transactions
from app.routes import analytics
from app.routes import sync
from app.routes import statements
from app.routes import budgets

# Configure structured logging (dev: human-friendly console; prod: JSON)
_is_prod = os.getenv("ENVIRONMENT", "development") == "production"
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer() if not _is_prod else structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Initialize FastAPI application
app = FastAPI(
    title="Gmail AI Expense Tracker API",
    description="""
    ## Automated Expense Tracking via Gmail Analysis
    
    This API provides automated expense tracking by analyzing transaction emails from Gmail.
    
    ### Features
    * 🔐 **Google OAuth Authentication** - Secure login with Gmail access
    * 📧 **Email Parsing** - Intelligent extraction of transaction details
    * 💰 **Transaction Management** - Track and categorize expenses
    * 📊 **Analytics** - Spending insights and trends
    * 🔄 **Auto-Sync** - Periodic Gmail synchronization
    
    ### Authentication
    Most endpoints require authentication via session cookie obtained through OAuth flow:
    1. Navigate to `/auth/google` to initiate OAuth
    2. Complete Google authorization
    3. Session cookie will be set automatically
    4. Use authenticated endpoints
    
    ### Quick Start
    1. **Health Check**: `GET /` - Verify API is running
    2. **Database Status**: `GET /debug/db` - Check database connection
    3. **Login**: `GET /auth/google` - Start OAuth flow
    4. **Get Profile**: `GET /auth/me` - View your profile (requires auth)
    5. **Sync Emails**: `POST /sync/manual` - Trigger email sync (requires auth)
    6. **View Transactions**: `GET /transactions` - List your expenses (requires auth)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Gmail Expense Tracker",
        "url": "http://localhost:5173",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "OAuth login, session management, and user profile endpoints"
        },
        {
            "name": "Transactions",
            "description": "Manage and query expense transactions"
        },
        {
            "name": "Analytics",
            "description": "Spending insights, trends, and statistics"
        },
        {
            "name": "Sync",
            "description": "Gmail synchronization and email processing"
        },
        {
            "name": "Statements",
            "description": "Upload bank/credit card statements (PDF, CSV) for analysis"
        },
        {
            "name": "Health",
            "description": "System health and diagnostic endpoints"
        }
    ]
)

# CORS Configuration (comma-separated CORS_ORIGINS env var)
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(sync.router)
app.include_router(statements.router)
app.include_router(budgets.router)

# Wire SlowAPI rate limiter (required for @limiter.limit decorators)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
app.state.limiter = sync.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Production error handler for sanitizing error messages
@app.exception_handler(Exception)
async def production_exception_handler(request: Request, exc: Exception):
    """
    Sanitize error messages in production environment.
    
    In production, returns generic error messages to avoid exposing
    internal implementation details, stack traces, or sensitive information.
    In development, returns detailed error information for debugging.
    """
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    
    if is_production:
        # Generic error message for production
        logger.error("production_error", 
                    error_type=type(exc).__name__,
                    path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal error occurred. Please try again later."}
        )
    else:
        # Detailed error for development
        import traceback
        logger.error("development_error",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    traceback=traceback.format_exc(),
                    path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "traceback": traceback.format_exc()
            }
        )


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Gmail AI Expense Tracker API",
        "version": "1.0.0"
    }


@app.get("/debug/db", tags=["Health"])
async def debug_database():
    """
    Debug endpoint to check database connection and tables.
    
    Disabled in production (set ENABLE_DEBUG_API=true for dev only).
    Returns minimal status when enabled to avoid information disclosure.
    """
    if os.getenv("ENABLE_DEBUG_API", "false").lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found"
        )

    from app.database import engine
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()

            return {
                "status": "connected",
                "database": db_name
            }
    except Exception as e:
        logger.error("debug_db_error", error=str(e), error_type=type(e).__name__)
        return {
            "status": "error",
            "message": "Database connection failed"
        }


@app.on_event("startup")
async def startup_event():
    """Application startup event handler"""
    logger.info("application_startup", message="Gmail AI Expense Tracker API starting up")
    
    # Start the sync scheduler
    from app.scheduler.sync_job import start_scheduler
    start_scheduler()
    logger.info("sync_scheduler_started")
    
    # Schedule OAuth state cleanup every 5 minutes
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app.auth.oauth import cleanup_expired_states
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cleanup_expired_states, 'interval', minutes=5)
    scheduler.start()
    logger.info("oauth_state_cleanup_scheduled")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler"""
    logger.info("application_shutdown", message="Gmail AI Expense Tracker API shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
