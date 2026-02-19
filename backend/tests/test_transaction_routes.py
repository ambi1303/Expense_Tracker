"""
Unit tests for transaction routes.

Tests the transaction API endpoints including listing and CSV export.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import delete

from app.models.user import User
from app.models.transaction import Transaction
from app.database import AsyncSessionLocal
from app.auth.jwt_handler import create_session_token


@pytest.mark.asyncio
async def test_list_transactions_empty(client):
    """Test listing transactions when user has no transactions."""
    # Create test user
    session = AsyncSessionLocal()
    test_user = User(
        id=uuid4(),
        email=f"test_{uuid4()}@example.com",
        name="Test User",
        google_id=f"google_{uuid4()}",
        refresh_token_encrypted="encrypted_token"
    )
    session.add(test_user)
    await session.commit()
    
    try:
        # Create JWT token
        token = create_session_token(str(test_user.id), test_user.email)
        
        # Make request
        response = await client.get(
            "/transactions",
            cookies={"session_token": token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["transactions"]) == 0
        assert data["page"] == 0
        assert data["limit"] == 50
        
    finally:
        await session.execute(delete(User).where(User.id == test_user.id))
        await session.commit()
        await session.close()


@pytest.mark.asyncio
async def test_list_transactions_with_data(client):
    """Test listing transactions when user has transactions."""
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid4(),
            email=f"test_{uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Create test transactions
        for i in range(5):
            transaction = Transaction(
                user_id=test_user.id,
                amount=Decimal(f"{100 + i}.00"),
                currency="INR",
                transaction_type="debit",
                merchant=f"Merchant {i}",
                transaction_date=datetime.now() - timedelta(days=i),
                bank_name="HDFC Bank",
                gmail_message_id=f"msg_{i}_{uuid4().hex[:8]}"
            )
            session.add(transaction)
        await session.commit()
        
        # Create JWT token
        token = create_session_token(str(test_user.id), test_user.email)
        
        # Make request
        response = await client.get(
            "/transactions",
            cookies={"session_token": token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["transactions"]) == 5
        
        # Verify transaction data
        first_tx = data["transactions"][0]
        assert "id" in first_tx
        assert "amount" in first_tx
        assert "currency" in first_tx
        assert "transaction_type" in first_tx
        assert "merchant" in first_tx
        assert "transaction_date" in first_tx
        assert "bank_name" in first_tx
        
    finally:
        if test_user:
            await session.execute(delete(Transaction).where(Transaction.user_id == test_user.id))
            await session.execute(delete(User).where(User.id == test_user.id))
            await session.commit()
        await session.close()


@pytest.mark.asyncio
async def test_list_transactions_pagination(client):
    """Test transaction pagination."""
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid4(),
            email=f"test_{uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Create 10 test transactions
        for i in range(10):
            transaction = Transaction(
                user_id=test_user.id,
                amount=Decimal(f"{100 + i}.00"),
                currency="INR",
                transaction_type="debit",
                merchant=f"Merchant {i}",
                transaction_date=datetime.now() - timedelta(days=i),
                bank_name="HDFC Bank",
                gmail_message_id=f"msg_{i}_{uuid4().hex[:8]}"
            )
            session.add(transaction)
        await session.commit()
        
        # Create JWT token
        token = create_session_token(str(test_user.id), test_user.email)
        
        # Request first page (limit 5)
        response = await client.get(
            "/transactions?limit=5&skip=0",
            cookies={"session_token": token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["transactions"]) == 5
        assert data["page"] == 0
        assert data["limit"] == 5
        
        # Request second page
        response = await client.get(
            "/transactions?limit=5&skip=5",
            cookies={"session_token": token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["transactions"]) == 5
        assert data["page"] == 1
        
    finally:
        if test_user:
            await session.execute(delete(Transaction).where(Transaction.user_id == test_user.id))
            await session.execute(delete(User).where(User.id == test_user.id))
            await session.commit()
        await session.close()


@pytest.mark.asyncio
async def test_list_transactions_filter_by_type(client):
    """Test filtering transactions by type."""
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid4(),
            email=f"test_{uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Create debit transactions
        for i in range(3):
            transaction = Transaction(
                user_id=test_user.id,
                amount=Decimal(f"{100 + i}.00"),
                currency="INR",
                transaction_type="debit",
                merchant=f"Merchant {i}",
                transaction_date=datetime.now() - timedelta(days=i),
                bank_name="HDFC Bank",
                gmail_message_id=f"msg_debit_{i}_{uuid4().hex[:8]}"
            )
            session.add(transaction)
        
        # Create credit transactions
        for i in range(2):
            transaction = Transaction(
                user_id=test_user.id,
                amount=Decimal(f"{200 + i}.00"),
                currency="INR",
                transaction_type="credit",
                merchant=f"Merchant Credit {i}",
                transaction_date=datetime.now() - timedelta(days=i),
                bank_name="ICICI Bank",
                gmail_message_id=f"msg_credit_{i}_{uuid4().hex[:8]}"
            )
            session.add(transaction)
        await session.commit()
        
        # Create JWT token
        token = create_session_token(str(test_user.id), test_user.email)
        
        # Filter by debit
        response = await client.get(
            "/transactions?transaction_type=debit",
            cookies={"session_token": token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert all(tx["transaction_type"] == "debit" for tx in data["transactions"])
        
        # Filter by credit
        response = await client.get(
            "/transactions?transaction_type=credit",
            cookies={"session_token": token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(tx["transaction_type"] == "credit" for tx in data["transactions"])
        
    finally:
        if test_user:
            await session.execute(delete(Transaction).where(Transaction.user_id == test_user.id))
            await session.execute(delete(User).where(User.id == test_user.id))
            await session.commit()
        await session.close()


@pytest.mark.asyncio
async def test_export_transactions_csv(client):
    """Test CSV export functionality."""
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid4(),
            email=f"test_{uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Create test transactions
        for i in range(3):
            transaction = Transaction(
                user_id=test_user.id,
                amount=Decimal(f"{100 + i}.00"),
                currency="INR",
                transaction_type="debit",
                merchant=f"Merchant {i}",
                transaction_date=datetime.now() - timedelta(days=i),
                bank_name="HDFC Bank",
                gmail_message_id=f"msg_{i}_{uuid4().hex[:8]}"
            )
            session.add(transaction)
        await session.commit()
        
        # Create JWT token
        token = create_session_token(str(test_user.id), test_user.email)
        
        # Request CSV export
        response = await client.get(
            "/transactions/export",
            cookies={"session_token": token}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "transactions_" in response.headers["content-disposition"]
        
        # Verify CSV content
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        
        # Check header
        assert "Date,Type,Amount,Currency,Merchant,Bank,Created At" in lines[0]
        
        # Check data rows (should have 3 transactions)
        assert len(lines) >= 4  # Header + 3 data rows
        
    finally:
        if test_user:
            await session.execute(delete(Transaction).where(Transaction.user_id == test_user.id))
            await session.execute(delete(User).where(User.id == test_user.id))
            await session.commit()
        await session.close()


@pytest.mark.asyncio
async def test_list_transactions_unauthorized(client):
    """Test that unauthorized requests are rejected."""
    response = await client.get("/transactions")
    assert response.status_code == 401
