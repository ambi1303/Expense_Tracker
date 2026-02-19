"""
Unit tests for Gmail service.

Tests the Gmail API integration including email fetching, search queries,
retry logic, and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from googleapiclient.errors import HttpError

from app.services.gmail_service import (
    fetch_transaction_emails,
    get_email_content,
    get_gmail_service,
    TRANSACTION_SEARCH_QUERY
)


@pytest.mark.asyncio
async def test_search_query_is_correctly_formatted():
    """
    Test search query is correctly formatted.
    
    **Validates: Requirements 3.1**
    """
    # The search query should contain the required terms
    assert "INR" in TRANSACTION_SEARCH_QUERY
    assert "Rs" in TRANSACTION_SEARCH_QUERY
    assert "debited" in TRANSACTION_SEARCH_QUERY
    assert "credited" in TRANSACTION_SEARCH_QUERY


@pytest.mark.asyncio
async def test_email_fetching_returns_subject_and_body():
    """
    Test email fetching returns subject and body.
    
    **Validates: Requirements 3.4**
    """
    # Mock Gmail API response
    mock_message = {
        'id': 'test_message_id',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Transaction Alert: Rs 500 debited'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
            ],
            'body': {
                'data': 'WW91ciBhY2NvdW50IGhhcyBiZWVuIGRlYml0ZWQgd2l0aCBScy41MDA='
            }
        }
    }
    
    # Mock Gmail service
    mock_service = Mock()
    mock_messages = Mock()
    mock_get = Mock()
    mock_get.execute.return_value = mock_message
    mock_messages.get.return_value = mock_get
    mock_service.users().messages.return_value = mock_messages
    
    with patch('app.services.gmail_service.get_gmail_service', return_value=mock_service):
        # Fetch email content
        email_data = await get_email_content('test_token', 'test_message_id')
        
        # Should have subject
        assert 'subject' in email_data
        assert 'Transaction Alert' in email_data['subject']
        
        # Should have body
        assert 'body' in email_data
        assert len(email_data['body']) > 0


@pytest.mark.asyncio
async def test_retry_logic_on_api_failures():
    """
    Test retry logic on API failures.
    
    **Validates: Requirements 3.1**
    """
    # Mock Gmail service that fails twice then succeeds
    call_count = [0]
    
    def mock_execute():
        call_count[0] += 1
        if call_count[0] < 3:
            # Simulate HTTP error
            response = Mock()
            response.status = 500
            raise HttpError(resp=response, content=b'Server error')
        # Third call succeeds
        return {
            'id': 'test_id',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test'},
                    {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
                ],
                'body': {'data': 'VGVzdA=='}
            }
        }
    
    mock_service = Mock()
    mock_messages = Mock()
    mock_get = Mock()
    mock_get.execute = mock_execute
    mock_messages.get.return_value = mock_get
    mock_service.users().messages.return_value = mock_messages
    
    with patch('app.services.gmail_service.get_gmail_service', return_value=mock_service):
        # Should succeed after retries
        email_data = await get_email_content('test_token', 'test_id')
        
        # Should have retried and eventually succeeded
        assert call_count[0] == 3
        assert email_data['message_id'] == 'test_id'


@pytest.mark.asyncio
async def test_error_handling_for_rate_limits():
    """
    Test error handling for rate limits.
    
    **Validates: Requirements 3.1**
    """
    # Mock Gmail service that returns rate limit error
    mock_service = Mock()
    mock_messages = Mock()
    mock_get = Mock()
    
    # Simulate rate limit error (429)
    response = Mock()
    response.status = 429
    mock_get.execute.side_effect = HttpError(resp=response, content=b'Rate limit exceeded')
    
    mock_messages.get.return_value = mock_get
    mock_service.users().messages.return_value = mock_messages
    
    with patch('app.services.gmail_service.get_gmail_service', return_value=mock_service):
        # Should raise HttpError after retries
        with pytest.raises(HttpError):
            await get_email_content('test_token', 'test_id')


@pytest.mark.asyncio
async def test_fetch_transaction_emails_with_search_query():
    """
    Test fetch_transaction_emails uses correct search query.
    
    **Validates: Requirements 3.1**
    """
    # Mock Gmail API list response
    mock_list_result = {
        'messages': [
            {'id': 'msg1'}
        ]
    }
    
    # Mock Gmail API get response
    mock_message = {
        'id': 'msg1',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Rs 100 debited'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
            ],
            'body': {'data': 'VHJhbnNhY3Rpb24='}
        }
    }
    
    # Mock Gmail service
    mock_service = Mock()
    mock_messages = Mock()
    
    # Mock list
    mock_list = Mock()
    mock_list.execute.return_value = mock_list_result
    mock_messages.list.return_value = mock_list
    
    # Mock get
    mock_get = Mock()
    mock_get.execute.return_value = mock_message
    mock_messages.get.return_value = mock_get
    
    mock_service.users().messages.return_value = mock_messages
    
    with patch('app.services.gmail_service.get_gmail_service', return_value=mock_service):
        # Fetch emails
        emails = await fetch_transaction_emails('test_token')
        
        # Verify list was called with correct query
        mock_messages.list.assert_called_once()
        call_kwargs = mock_messages.list.call_args[1]
        
        # Should use the transaction search query
        assert 'q' in call_kwargs
        assert TRANSACTION_SEARCH_QUERY in call_kwargs['q']


@pytest.mark.asyncio
async def test_fetch_emails_with_date_filter():
    """
    Test fetch_transaction_emails with date filter.
    
    **Validates: Requirements 3.1**
    """
    from datetime import datetime
    
    # Mock Gmail API
    mock_list_result = {'messages': []}
    
    mock_service = Mock()
    mock_messages = Mock()
    mock_list = Mock()
    mock_list.execute.return_value = mock_list_result
    mock_messages.list.return_value = mock_list
    mock_service.users().messages.return_value = mock_messages
    
    with patch('app.services.gmail_service.get_gmail_service', return_value=mock_service):
        # Fetch emails with date filter
        last_sync = datetime(2024, 1, 1)
        await fetch_transaction_emails('test_token', last_sync_time=last_sync)
        
        # Verify list was called with date filter
        call_kwargs = mock_messages.list.call_args[1]
        assert 'q' in call_kwargs
        assert 'after:2024/01/01' in call_kwargs['q']


@pytest.mark.asyncio
async def test_multipart_email_body_extraction():
    """
    Test extraction of body from multipart emails.
    
    **Validates: Requirements 3.4**
    """
    # Mock multipart email
    mock_message = {
        'id': 'test_id',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
            ],
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {'data': 'UGFydCAxIGJvZHk='}
                },
                {
                    'mimeType': 'text/html',
                    'body': {'data': 'UGFydCAyIGJvZHk='}
                }
            ]
        }
    }
    
    mock_service = Mock()
    mock_messages = Mock()
    mock_get = Mock()
    mock_get.execute.return_value = mock_message
    mock_messages.get.return_value = mock_get
    mock_service.users().messages.return_value = mock_messages
    
    with patch('app.services.gmail_service.get_gmail_service', return_value=mock_service):
        # Fetch email
        email_data = await get_email_content('test_token', 'test_id')
        
        # Should extract body from parts
        assert 'body' in email_data
        assert len(email_data['body']) > 0


@pytest.mark.asyncio
async def test_empty_message_list_returns_empty_array():
    """
    Test that empty message list returns empty array.
    
    **Validates: Requirements 3.1**
    """
    # Mock Gmail API with no messages
    mock_list_result = {'messages': []}
    
    mock_service = Mock()
    mock_messages = Mock()
    mock_list = Mock()
    mock_list.execute.return_value = mock_list_result
    mock_messages.list.return_value = mock_list
    mock_service.users().messages.return_value = mock_messages
    
    with patch('app.services.gmail_service.get_gmail_service', return_value=mock_service):
        # Fetch emails
        emails = await fetch_transaction_emails('test_token')
        
        # Should return empty list
        assert isinstance(emails, list)
        assert len(emails) == 0


@pytest.mark.asyncio
async def test_invalid_access_token_raises_error():
    """
    Test that invalid access token raises error.
    
    **Validates: Requirements 3.1**
    """
    # Empty token should raise ValueError
    with pytest.raises(ValueError, match="Access token cannot be empty"):
        get_gmail_service("")
