"""
Property-based test for email content completeness.

Feature: gmail-expense-tracker
Property 8: Email Content Completeness

**Validates: Requirements 3.4**

For any new email fetched from Gmail API, the returned data should include 
both subject and body fields.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, AsyncMock

from app.services.gmail_service import get_email_content, fetch_transaction_emails


# Strategy for generating message IDs
message_id_strategy = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122, 
                          blacklist_categories=('Cc', 'Cs')),
    min_size=10,
    max_size=30
)

# Strategy for generating access tokens
access_token_strategy = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122, 
                          blacklist_categories=('Cc', 'Cs')),
    min_size=20,
    max_size=100
)


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=30)
@given(access_token=access_token_strategy, message_id=message_id_strategy)
async def test_email_content_includes_subject_and_body(access_token, message_id):
    """
    Property 8: Email Content Completeness
    
    **Validates: Requirements 3.4**
    
    For any email fetched from Gmail API, the returned data should include 
    both subject and body fields.
    """
    # Mock Gmail API response
    mock_message = {
        'id': message_id,
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test Transaction Email'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
            ],
            'body': {
                'data': 'VGVzdCBlbWFpbCBib2R5IGNvbnRlbnQ='  # Base64 encoded
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
        email_data = await get_email_content(access_token, message_id)
        
        # Should include subject field
        assert 'subject' in email_data, \
            "Email data should include 'subject' field"
        assert isinstance(email_data['subject'], str), \
            "Subject should be a string"
        
        # Should include body field
        assert 'body' in email_data, \
            "Email data should include 'body' field"
        assert isinstance(email_data['body'], str), \
            "Body should be a string"
        
        # Should include message_id field
        assert 'message_id' in email_data, \
            "Email data should include 'message_id' field"
        assert email_data['message_id'] == message_id, \
            "Message ID should match the requested ID"


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=20)
@given(access_token=access_token_strategy, message_id=message_id_strategy)
async def test_email_content_fields_are_not_none(access_token, message_id):
    """
    Property 8: Email Content Completeness
    
    **Validates: Requirements 3.4**
    
    For any email fetched, subject and body fields should not be None.
    """
    # Mock Gmail API response
    mock_message = {
        'id': message_id,
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Transaction Alert'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
            ],
            'body': {
                'data': 'VHJhbnNhY3Rpb24gZGV0YWlscw=='
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
        email_data = await get_email_content(access_token, message_id)
        
        # Subject should not be None
        assert email_data['subject'] is not None, \
            "Subject should not be None"
        
        # Body should not be None
        assert email_data['body'] is not None, \
            "Body should not be None"


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=20)
@given(access_token=access_token_strategy)
async def test_fetch_transaction_emails_returns_complete_data(access_token):
    """
    Property 8: Email Content Completeness
    
    **Validates: Requirements 3.4**
    
    For any batch of emails fetched, each email should have complete data.
    """
    # Mock Gmail API list response
    mock_list_result = {
        'messages': [
            {'id': 'msg1'},
            {'id': 'msg2'}
        ]
    }
    
    # Mock Gmail API get responses
    mock_message1 = {
        'id': 'msg1',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Transaction 1'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
            ],
            'body': {'data': 'Qm9keSAx'}
        }
    }
    
    mock_message2 = {
        'id': 'msg2',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Transaction 2'},
                {'name': 'Date', 'value': 'Tue, 2 Jan 2024 12:00:00 +0000'}
            ],
            'body': {'data': 'Qm9keSAy'}
        }
    }
    
    # Mock Gmail service
    mock_service = Mock()
    mock_messages = Mock()
    
    # Mock list
    mock_list = Mock()
    mock_list.execute.return_value = mock_list_result
    mock_messages.list.return_value = mock_list
    
    # Mock get (return different messages based on call)
    call_count = [0]
    def mock_get_side_effect(userId, id, format):
        mock_get = Mock()
        if call_count[0] == 0:
            mock_get.execute.return_value = mock_message1
        else:
            mock_get.execute.return_value = mock_message2
        call_count[0] += 1
        return mock_get
    
    mock_messages.get.side_effect = mock_get_side_effect
    mock_service.users().messages.return_value = mock_messages
    
    with patch('app.services.gmail_service.get_gmail_service', return_value=mock_service):
        # Fetch transaction emails
        emails = await fetch_transaction_emails(access_token)
        
        # Should return a list
        assert isinstance(emails, list), "Should return a list of emails"
        
        # Each email should have complete data
        for email in emails:
            assert 'subject' in email, "Each email should have subject"
            assert 'body' in email, "Each email should have body"
            assert 'message_id' in email, "Each email should have message_id"
            
            assert isinstance(email['subject'], str), "Subject should be string"
            assert isinstance(email['body'], str), "Body should be string"
            assert isinstance(email['message_id'], str), "Message ID should be string"


@pytest.mark.property
@pytest.mark.asyncio
async def test_empty_message_id_raises_error():
    """
    Property 8: Email Content Completeness
    
    **Validates: Requirements 3.4**
    
    Attempting to fetch email with empty message ID should raise an error.
    """
    with pytest.raises(ValueError, match="Message ID cannot be empty"):
        await get_email_content("valid_token", "")


@pytest.mark.property
@pytest.mark.asyncio
async def test_empty_access_token_raises_error():
    """
    Property 8: Email Content Completeness
    
    **Validates: Requirements 3.4**
    
    Attempting to fetch email with empty access token should raise an error.
    """
    with pytest.raises(ValueError, match="Access token cannot be empty"):
        await get_email_content("", "message_id_123")


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=20)
@given(access_token=access_token_strategy, message_id=message_id_strategy)
async def test_email_content_includes_date_field(access_token, message_id):
    """
    Property 8: Email Content Completeness
    
    **Validates: Requirements 3.4**
    
    For any email fetched, the data should include a date field.
    """
    # Mock Gmail API response
    mock_message = {
        'id': message_id,
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test Email'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
            ],
            'body': {'data': 'VGVzdA=='}
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
        email_data = await get_email_content(access_token, message_id)
        
        # Should include date field
        assert 'date' in email_data, \
            "Email data should include 'date' field"
