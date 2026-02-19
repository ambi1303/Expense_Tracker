"""
Gmail AI Expense Tracker - Main Application Entry Point
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

# Load environment variables from .env file (or .evn if that's what exists)
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists(".evn"):
    load_dotenv(".evn")

# Import routers
from app.routes import auth
from app.routes import transactions
from app.routes import analytics
from app.routes import sync

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Initialize FastAPI application
app = FastAPI(
    title="Gmail AI Expense Tracker API",
    description="Automated expense tracking by analyzing Gmail transaction emails",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
# TODO: Configure with environment variable for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(sync.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Gmail AI Expense Tracker API",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event handler"""
    logger.info("application_startup", message="Gmail AI Expense Tracker API starting up")
    
    # Start the sync scheduler
    from app.scheduler.sync_job import start_scheduler
    start_scheduler()
    logger.info("sync_scheduler_started")


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
