"""
Run this script ONCE locally to generate the secret keys you need to set
in your Vercel dashboard: Settings > Environment Variables
"""
import secrets
from cryptography.fernet import Fernet

secret_key = secrets.token_urlsafe(48)
fernet_key = Fernet.generate_key().decode()
cron_secret = secrets.token_urlsafe(32)

print("\n" + "="*60)
print("  COPY THESE INTO VERCEL > Settings > Environment Variables")
print("="*60)
print(f"\nSECRET_KEY={secret_key}")
print(f"TOKEN_ENCRYPTION_KEY={fernet_key}")
print(f"CRON_SECRET={cron_secret}")
print(f"\nDEBUG=False")
print(f"DEMO_MODE=False")
print(f"DATABASE_URL=sqlite:///./social_growth.db")
print("\n" + "="*60)
print("  Also add your API keys if you have them:")
print("="*60)
print("GEMINI_API_KEY=<your-gemini-api-key>")
print("GROQ_API_KEY=<your-groq-api-key>")
print("FACEBOOK_APP_ID=<your-facebook-app-id>")
print("FACEBOOK_CLIENT_SECRET=<your-facebook-client-secret>")
print("FACEBOOK_REDIRECT_URI=https://ai-social-media-crm-ql4y.vercel.app/api/auth/facebook/callback")
print()
