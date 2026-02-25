"""Debug script to test Gmail API and email parsing."""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.gmail_service import fetch_transaction_emails
from app.services.email_parser import parse_email
from app.auth.encryption import decrypt_refresh_token
from app.auth.oauth import refresh_access_token

async def debug_gmail_fetch():
    print("=" * 60)
    print("GMAIL FETCH DEBUG")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        # Get first user
        result = await session.execute(select(User))
        user = result.scalars().first()
        
        if not user:
            print("\n❌ No users found in database")
            print("   Please complete OAuth login first")
            return
        
        print(f"\n✅ Found user: {user.email}")
        print(f"   User ID: {user.id}")
        
        try:
            # Decrypt and refresh token
            print("\n📝 Refreshing access token...")
            refresh_token = decrypt_refresh_token(user.refresh_token_encrypted)
            access_token = await refresh_access_token(refresh_token)
            print("✅ Access token refreshed")
            
            # Fetch emails
            print("\n📧 Fetching transaction emails from Gmail...")
            emails = await fetch_transaction_emails(access_token)
            
            print(f"\n✅ Fetched {len(emails)} emails")
            
            if not emails:
                print("\n⚠️  No emails found matching query:")
                print('   ("INR" OR "Rs" OR "debited" OR "credited")')
                print("\n   Possible reasons:")
                print("   1. No transaction emails in your Gmail")
                print("   2. Gmail API permissions not granted")
                print("   3. Search query not matching your emails")
                return
            
            # Show first few emails
            print("\n📋 Sample emails:")
            for i, email in enumerate(emails[:3], 1):
                print(f"\n   Email {i}:")
                print(f"   Message ID: {email.get('message_id', 'N/A')}")
                print(f"   Subject: {email.get('subject', 'N/A')[:60]}...")
                
                # Try parsing
                parsed = parse_email(
                    email.get('subject', ''),
                    email.get('body', '')
                )
                
                if parsed:
                    print(f"   ✅ Parsed: Rs {parsed.amount} {parsed.transaction_type.value}")
                    print(f"      Date: {parsed.transaction_date}")
                    print(f"      Merchant: {parsed.merchant or 'N/A'}")
                else:
                    print(f"   ❌ Failed to parse")
                    print(f"      Subject: {email.get('subject', '')[:100]}")
                    print(f"      Body preview: {email.get('body', '')[:100]}...")
            
            # Count parseable emails
            parseable = sum(1 for e in emails if parse_email(e.get('subject', ''), e.get('body', '')))
            print(f"\n📊 Summary:")
            print(f"   Total emails: {len(emails)}")
            print(f"   Parseable: {parseable}")
            print(f"   Unparseable: {len(emails) - parseable}")
            
            if parseable == 0:
                print("\n⚠️  No emails could be parsed!")
                print("   This means the email format doesn't match the parser patterns")
                print("   Check the email samples above to see why")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_gmail_fetch())
