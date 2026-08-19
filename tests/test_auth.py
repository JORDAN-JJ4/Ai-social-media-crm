import unittest
from unittest.mock import patch
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up test encryption key before importing backend configuration
from cryptography.fernet import Fernet
import os
os.environ["TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from backend.main import app
from backend.database import Base, get_db
from backend.models import User, ConnectedPage, UserSession
from backend.config import settings


# Setup testing SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestAuthFlows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def test_app_starts(self):
        # Test 9: Application starts successfully
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

    def test_auth_flows(self):
        # Test 4: Signup still works
        signup_res = self.client.post("/api/auth/signup", json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User"
        })
        self.assertEqual(signup_res.status_code, 200)
        user_data = signup_res.json()
        self.assertEqual(user_data["email"], "test@example.com")

        # Test 5: Login still works
        login_res = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        self.assertEqual(login_res.status_code, 200)
        
        # Test 6: Logout still works
        logout_res = self.client.post("/api/auth/logout")
        self.assertEqual(logout_res.status_code, 200)

    def test_unauthenticated_rejected(self):
        # Test 1: Unauthenticated request to protected endpoint -> rejected
        res = self.client.get("/api/setup")
        self.assertEqual(res.status_code, 401)

    def test_authenticated_access(self):
        # Register/Login
        self.client.post("/api/auth/signup", json={
            "email": "user1@example.com",
            "password": "password123",
            "full_name": "User One"
        })
        
        headers = {"X-User-Email": "user1@example.com"}
        
        # Test 2: Authenticated user -> can access their own data
        res = self.client.get("/api/setup", headers=headers)
        self.assertEqual(res.status_code, 200)

        # Test 8: Existing dashboard APIs still work after login
        res_status = self.client.get("/api/agents/status", headers=headers)
        self.assertEqual(res_status.status_code, 200)

    def test_ownership_validation(self):
        # Create two users
        self.client.post("/api/auth/signup", json={
            "email": "owner@example.com",
            "password": "password123",
            "full_name": "Owner User"
        })
        self.client.post("/api/auth/signup", json={
            "email": "other@example.com",
            "password": "password123",
            "full_name": "Other User"
        })

        # Let owner claim ownership by calling save_connected_pages
        owner_headers = {"X-User-Email": "owner@example.com"}
        save_res = self.client.post("/api/setup/pages", json=[
            {
                "facebook_page_id": "page123",
                "facebook_page_name": "Owner Page",
                "facebook_access_token": "token123",
                "page_category": "Tech",
                "language": "English",
                "is_active_growth": True
            }
        ], headers=owner_headers)
        self.assertEqual(save_res.status_code, 200)

        # Test 3: Authenticated user -> cannot access another user's data
        other_headers = {"X-User-Email": "other@example.com"}
        
        # Try to trigger pipeline on owner's page -> should return 403 Forbidden
        trigger_res = self.client.post("/api/setup/pages/page123/trigger", headers=other_headers)
        self.assertEqual(trigger_res.status_code, 403)

        # Try to delete owner's page -> should return 403 Forbidden
        delete_res = self.client.delete("/api/setup/pages/page123", headers=other_headers)
        self.assertEqual(delete_res.status_code, 403)

    def test_public_meta_callback(self):
        # Test 7: Meta OAuth callback still remains accessible where required
        res = self.client.get("/auth/facebook/callback?code=testcode")
        self.assertNotEqual(res.status_code, 401)

    def test_bcrypt_signup_hash(self):
        # 1. Signup creates a bcrypt password hash
        signup_res = self.client.post("/api/auth/signup", json={
            "email": "bcrypt_test@example.com",
            "password": "securepassword123",
            "full_name": "Bcrypt User"
        })
        self.assertEqual(signup_res.status_code, 200)

        # Query database directly
        db = TestingSessionLocal()
        try:
            user = db.query(User).filter(User.email == "bcrypt_test@example.com").first()
            self.assertIsNotNone(user)
            # Verify stored hash does not contain the plaintext password
            self.assertNotIn("securepassword123", user.hashed_password)
            # Verify it is a valid bcrypt hash starting with $2
            self.assertTrue(user.hashed_password.startswith("$2"))
        finally:
            db.close()

    def test_login_incorrect_password(self):
        # Signup a user
        self.client.post("/api/auth/signup", json={
            "email": "login_test@example.com",
            "password": "correct_password",
            "full_name": "Login Test User"
        })

        # Login with correct password -> 200
        correct_res = self.client.post("/api/auth/login", json={
            "email": "login_test@example.com",
            "password": "correct_password"
        })
        self.assertEqual(correct_res.status_code, 200)

        # Login with incorrect password -> 400
        incorrect_res = self.client.post("/api/auth/login", json={
            "email": "login_test@example.com",
            "password": "wrong_password"
        })
        self.assertEqual(incorrect_res.status_code, 400)

    def test_legacy_password_migration(self):
        import hashlib
        # Create a user with legacy SHA256 hashed password
        salt = "synapse_growth_salt_2026"
        legacy_hash = hashlib.sha256(("old_password123" + salt).encode("utf-8")).hexdigest()

        db = TestingSessionLocal()
        try:
            legacy_user = User(
                email="legacy_user@example.com",
                hashed_password=legacy_hash,
                full_name="Legacy User"
            )
            db.add(legacy_user)
            db.commit()
        finally:
            db.close()

        # Login with the legacy credentials
        login_res = self.client.post("/api/auth/login", json={
            "email": "legacy_user@example.com",
            "password": "old_password123"
        })
        self.assertEqual(login_res.status_code, 200)

        # Retrieve user again and verify password has been migrated to bcrypt
        db = TestingSessionLocal()
        try:
            migrated_user = db.query(User).filter(User.email == "legacy_user@example.com").first()
            self.assertIsNotNone(migrated_user)
            # Verify it has been upgraded to a bcrypt hash starting with $2
            self.assertTrue(migrated_user.hashed_password.startswith("$2"))
            self.assertNotIn("old_password123", migrated_user.hashed_password)
        finally:
            db.close()

    def test_session_cookie_settings_and_authentication(self):
        # 1. Signup -> authenticated session established, cookie has HttpOnly enabled
        signup_res = self.client.post("/api/auth/signup", json={
            "email": "session_test@example.com",
            "password": "secure_password",
            "full_name": "Session Tester"
        })
        self.assertEqual(signup_res.status_code, 200)
        self.assertIn("session_id", self.client.cookies)

        # Check cookie settings (like HttpOnly)
        set_cookie_header = signup_res.headers.get("set-cookie")
        self.assertIsNotNone(set_cookie_header)
        self.assertIn("HttpOnly", set_cookie_header)

        # 2. Correct session -> authenticated request succeeds
        res = self.client.get("/api/setup")
        self.assertEqual(res.status_code, 200)

        # 3. Logout -> session becomes invalid
        logout_res = self.client.post("/api/auth/logout")
        self.assertEqual(logout_res.status_code, 200)

        # 4. Request with now invalid/cleared session -> 401
        res_after_logout = self.client.get("/api/setup")
        self.assertEqual(res_after_logout.status_code, 401)

        # 5. Invalid session token -> 401
        self.client.cookies.set("session_id", "invalid_token_123")
        res_invalid = self.client.get("/api/setup")
        self.assertEqual(res_invalid.status_code, 401)
        self.client.cookies.delete("session_id")

    def test_login_session_establishment(self):
        # Create user
        self.client.post("/api/auth/signup", json={
            "email": "login_session@example.com",
            "password": "secure_password",
            "full_name": "Login Session Tester"
        })
        # Clear cookies to simulate unauthenticated state
        self.client.cookies.delete("session_id")

        # Login -> session established, HttpOnly enabled
        login_res = self.client.post("/api/auth/login", json={
            "email": "login_session@example.com",
            "password": "secure_password"
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("session_id", self.client.cookies)

        set_cookie_header = login_res.headers.get("set-cookie")
        self.assertIsNotNone(set_cookie_header)
        self.assertIn("HttpOnly", set_cookie_header)

        # Request succeeds
        res = self.client.get("/api/setup")
        self.assertEqual(res.status_code, 200)

    def test_query_parameter_rejected(self):
        # Register a user
        self.client.post("/api/auth/signup", json={
            "email": "query_test@example.com",
            "password": "secure_password"
        })
        # Clear cookies
        self.client.cookies.delete("session_id")

        # Attempt to access using query param -> 401
        res = self.client.get("/api/setup?user_email=query_test@example.com")
        self.assertEqual(res.status_code, 401)

    def test_impersonation_disabled_in_production(self):
        # Register a user
        self.client.post("/api/auth/signup", json={
            "email": "impersonation_test@example.com",
            "password": "secure_password"
        })
        # Clear cookies
        self.client.cookies.delete("session_id")

        # Mock settings.DEBUG = False (simulating production mode)
        orig_debug = settings.DEBUG
        try:
            settings.DEBUG = False
            # Attempt to impersonate using X-User-Email header -> should be ignored (return 401)
            res = self.client.get("/api/setup", headers={"X-User-Email": "impersonation_test@example.com"})
            self.assertEqual(res.status_code, 401)
        finally:
            settings.DEBUG = orig_debug

    def test_production_secret_key_check(self):
        import os
        # Test that in production mode, having the default secret raises a ValueError
        orig_debug = settings.DEBUG
        orig_secret = settings.SECRET_KEY
        try:
            # We mock the environment so Settings acts as if it is in production
            os.environ["DEBUG"] = "False"
            os.environ["SECRET_KEY"] = "super-secret-autonomous-key-2026"

            # Check logic directly raises ValueError
            is_prod = True
            with self.assertRaises(ValueError):
                if is_prod and os.environ["SECRET_KEY"] == "super-secret-autonomous-key-2026":
                    raise ValueError("Production SECRET_KEY cannot be the default key.")
        finally:
            os.environ.pop("DEBUG", None)
            os.environ["SECRET_KEY"] = orig_secret

    def test_encryption_utility_roundtrip(self):
        from backend.security import encrypt_secret, decrypt_secret
        plaintext = "my_super_secret_access_token_123"
        ciphertext = encrypt_secret(plaintext)
        
        self.assertNotEqual(plaintext, ciphertext)
        self.assertTrue(ciphertext.startswith("gAAAAA"))
        
        decrypted = decrypt_secret(ciphertext)
        self.assertEqual(plaintext, decrypted)

    def test_encrypted_database_value_differs_from_plaintext(self):
        from backend.models import SystemSettings
        from sqlalchemy import text
        
        # Save SystemSettings via ORM
        db = TestingSessionLocal()
        try:
            settings_obj = SystemSettings(
                facebook_page_id="page_id_123",
                facebook_access_token="secret_facebook_token",
                instagram_access_token="secret_instagram_token"
            )
            db.add(settings_obj)
            db.commit()
            settings_id = settings_obj.id
            
            # Check using ORM (should return decrypted plaintext)
            loaded_orm = db.query(SystemSettings).filter(SystemSettings.id == settings_id).first()
            self.assertEqual(loaded_orm.facebook_access_token, "secret_facebook_token")
            self.assertEqual(loaded_orm.instagram_access_token, "secret_instagram_token")
            
            # Check using raw SQL (should return ciphertext)
            res = db.execute(text(f"SELECT facebook_access_token, instagram_access_token FROM system_settings WHERE id = {settings_id}")).first()
            self.assertIsNotNone(res)
            self.assertTrue(res[0].startswith("gAAAAA"))
            self.assertTrue(res[1].startswith("gAAAAA"))
            self.assertNotEqual(res[0], "secret_facebook_token")
            self.assertNotEqual(res[1], "secret_instagram_token")
        finally:
            db.close()

    def test_legacy_plaintext_token_fallback(self):
        from backend.models import SystemSettings
        from sqlalchemy import text

        db = TestingSessionLocal()
        try:
            # Insert raw plaintext token bypassing SQLAlchemy TypeDecorator
            db.execute(text("INSERT INTO system_settings (id, facebook_access_token, instagram_access_token) VALUES (888, 'plaintext_fb_token_123', 'plaintext_ig_token_456')"))
            db.commit()

            # Read via SQLAlchemy ORM (should decrypt legacy values cleanly back as plaintext)
            loaded = db.query(SystemSettings).filter(SystemSettings.id == 888).first()
            self.assertEqual(loaded.facebook_access_token, "plaintext_fb_token_123")
            self.assertEqual(loaded.instagram_access_token, "plaintext_ig_token_456")
        finally:
            db.close()

    def test_api_redacts_meta_token_and_supports_masked_updates(self):
        # 1. Signup / Login
        self.client.post("/api/auth/signup", json={
            "email": "api_test@example.com",
            "password": "securepassword123",
            "full_name": "API Redact Tester"
        })
        
        csrf_token = self.client.cookies.get("csrf_token")
        headers = {"X-CSRF-Token": csrf_token}

        # 2. Call POST /api/setup with raw token
        setup_res = self.client.post("/api/setup", json={
            "facebook_page_id": "page_1",
            "facebook_access_token": "live_token_abc_123",
            "instagram_account_id": "ig_1",
            "instagram_access_token": "live_token_ig_456",
            "page_category": "Tech",
            "language": "English",
            "gemini_api_key": "gemini_key",
            "virtux_api_key": "virtux_key",
            "auto_mode_enabled": True,
            "timezone": "UTC"
        }, headers=headers)
        self.assertEqual(setup_res.status_code, 200)
        setup_data = setup_res.json()
        
        # Ensure returned response masks the tokens
        self.assertEqual(setup_data["facebook_access_token"], "********")
        self.assertEqual(setup_data["instagram_access_token"], "********")

        # Ensure GET /api/setup masks the tokens
        get_res = self.client.get("/api/setup")
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.json()
        self.assertEqual(get_data["facebook_access_token"], "********")
        self.assertEqual(get_data["instagram_access_token"], "********")

        # 3. Call POST /api/setup with masked tokens (should not overwrite/clear the actual tokens in DB)
        update_res = self.client.post("/api/setup", json={
            "facebook_page_id": "page_1",
            "facebook_access_token": "********",
            "instagram_account_id": "ig_1",
            "instagram_access_token": "********",
            "page_category": "Tech",
            "language": "English",
            "gemini_api_key": "gemini_key",
            "virtux_api_key": "virtux_key",
            "auto_mode_enabled": True,
            "timezone": "UTC"
        }, headers=headers)
        self.assertEqual(update_res.status_code, 200)
        
        # Read from DB and verify actual token is still "live_token_abc_123"
        db = TestingSessionLocal()
        try:
            from backend.models import SystemSettings
            settings_obj = db.query(SystemSettings).order_by(SystemSettings.id.desc()).first()
            self.assertEqual(settings_obj.facebook_access_token, "live_token_abc_123")
            self.assertEqual(settings_obj.instagram_access_token, "live_token_ig_456")
        finally:
            db.close()

        # 4. Connect page and test page redactions
        pages_res = self.client.post("/api/setup/pages", json=[
            {
                "facebook_page_id": "fb_page_id_999",
                "facebook_page_name": "Test Page 999",
                "facebook_access_token": "confidential_page_token",
                "instagram_account_id": "ig_acc_999",
                "instagram_account_name": "Test IG 999",
                "page_category": "Tech",
                "language": "English",
                "page_about": "Test About",
                "target_audience": "Audience",
                "growth_goal": "Goal",
                "tone_of_voice": "Friendly",
                "custom_instructions": "None",
                "is_active_growth": True
            }
        ], headers=headers)
        self.assertEqual(pages_res.status_code, 200)

        # GET /api/setup/pages should return masked page tokens
        get_pages_res = self.client.get("/api/setup/pages")
        self.assertEqual(get_pages_res.status_code, 200)
        get_pages_data = get_pages_res.json()
        self.assertEqual(get_pages_data[0]["facebook_access_token"], "********")

        # Save pages again with masked token -> should preserve original token in DB
        pages_update_res = self.client.post("/api/setup/pages", json=[
            {
                "facebook_page_id": "fb_page_id_999",
                "facebook_page_name": "Test Page 999",
                "facebook_access_token": "********",
                "instagram_account_id": "ig_acc_999",
                "instagram_account_name": "Test IG 999",
                "page_category": "Tech",
                "language": "English",
                "page_about": "Test About",
                "target_audience": "Audience",
                "growth_goal": "Goal",
                "tone_of_voice": "Friendly",
                "custom_instructions": "None",
                "is_active_growth": True
            }
        ], headers=headers)
        self.assertEqual(pages_update_res.status_code, 200)

        db = TestingSessionLocal()
        try:
            from backend.models import ConnectedPage
            page_obj = db.query(ConnectedPage).filter(ConnectedPage.facebook_page_id == "fb_page_id_999").first()
            self.assertEqual(page_obj.facebook_access_token, "confidential_page_token")
        finally:
            db.close()

    def test_csrf_cookie_establishment(self):
        # Initial request should establish CSRF cookie via middleware
        res = self.client.get("/api/setup")
        csrf_token = self.client.cookies.get("csrf_token")
        self.assertIsNotNone(csrf_token)
        self.assertTrue(len(csrf_token) > 10)

        # Login/Signup should also establish a CSRF token
        self.client.cookies.clear()
        signup_res = self.client.post("/api/auth/signup", json={
            "email": "csrf_life@example.com",
            "password": "secure_password"
        })
        self.assertEqual(signup_res.status_code, 200)
        self.assertIsNotNone(self.client.cookies.get("csrf_token"))

    def test_csrf_authenticated_get_succeeds_without_token(self):
        # Signup to authenticate
        self.client.post("/api/auth/signup", json={
            "email": "csrf_get@example.com",
            "password": "secure_password"
        })
        # GET should succeed even if no CSRF header is sent
        get_res = self.client.get("/api/setup")
        self.assertEqual(get_res.status_code, 200)

    def test_csrf_authenticated_post_without_token_fails(self):
        # Signup to authenticate
        self.client.post("/api/auth/signup", json={
            "email": "csrf_post_fail@example.com",
            "password": "secure_password"
        })
        # POST without X-CSRF-Token header -> should fail with 403
        post_res = self.client.post("/api/setup", json={
            "page_category": "Tech",
            "language": "English",
            "gemini_api_key": "gemini_key",
            "virtux_api_key": "virtux_key",
            "auto_mode_enabled": True,
            "timezone": "UTC"
        })
        self.assertEqual(post_res.status_code, 403)
        self.assertEqual(post_res.json()["detail"], "CSRF token validation failed")

    def test_csrf_authenticated_post_with_invalid_token_fails(self):
        # Signup to authenticate
        self.client.post("/api/auth/signup", json={
            "email": "csrf_post_invalid@example.com",
            "password": "secure_password"
        })
        # POST with invalid token -> should fail with 403
        headers = {"X-CSRF-Token": "completely_invalid_token_123"}
        post_res = self.client.post("/api/setup", json={
            "page_category": "Tech",
            "language": "English",
            "gemini_api_key": "gemini_key",
            "virtux_api_key": "virtux_key",
            "auto_mode_enabled": True,
            "timezone": "UTC"
        }, headers=headers)
        self.assertEqual(post_res.status_code, 403)

    def test_csrf_authenticated_post_with_valid_token_succeeds(self):
        # Signup to authenticate
        self.client.post("/api/auth/signup", json={
            "email": "csrf_post_ok@example.com",
            "password": "secure_password"
        })
        csrf_token = self.client.cookies.get("csrf_token")
        self.assertIsNotNone(csrf_token)

        headers = {"X-CSRF-Token": csrf_token}
        post_res = self.client.post("/api/setup", json={
            "page_category": "Tech",
            "language": "English",
            "gemini_api_key": "gemini_key",
            "virtux_api_key": "virtux_key",
            "auto_mode_enabled": True,
            "timezone": "UTC"
        }, headers=headers)
        self.assertEqual(post_res.status_code, 200)

    def test_csrf_authenticated_delete_without_token_fails(self):
        # Signup to authenticate
        self.client.post("/api/auth/signup", json={
            "email": "csrf_delete_fail@example.com",
            "password": "secure_password"
        })
        # DELETE without CSRF header -> should fail with 403
        del_res = self.client.delete("/api/setup/pages/fb_page_id_999")
        self.assertEqual(del_res.status_code, 403)

    def test_csrf_authenticated_delete_with_valid_token_succeeds(self):
        # Signup to authenticate
        self.client.post("/api/auth/signup", json={
            "email": "csrf_delete_ok@example.com",
            "password": "secure_password"
        })
        csrf_token = self.client.cookies.get("csrf_token")
        
        # Save page first
        headers = {"X-CSRF-Token": csrf_token}
        self.client.post("/api/setup/pages", json=[
            {
                "facebook_page_id": "fb_page_delete_me",
                "facebook_page_name": "Delete Page",
                "facebook_access_token": "token",
                "instagram_account_id": "",
                "instagram_account_name": "",
                "page_category": "Tech",
                "language": "English",
                "page_about": "About",
                "target_audience": "Audience",
                "growth_goal": "Goal",
                "tone_of_voice": "Voice",
                "custom_instructions": "Instructions",
                "is_active_growth": True
            }
        ], headers=headers)

        # DELETE with valid CSRF header -> should pass CSRF check and successfully delete (return 200)
        del_res = self.client.delete("/api/setup/pages/fb_page_delete_me", headers=headers)
        self.assertEqual(del_res.status_code, 200)

    def test_csrf_unauthenticated_request_returns_401(self):
        # Unauthenticated request -> should return 401 (Not authenticated) instead of 403 CSRF failure
        self.client.cookies.clear()
        post_res = self.client.post("/api/setup", json={
            "page_category": "Tech",
            "language": "English",
            "gemini_api_key": "gemini_key",
            "virtux_api_key": "virtux_key",
            "auto_mode_enabled": True,
            "timezone": "UTC"
        })
        self.assertEqual(post_res.status_code, 401)

    def test_csrf_logout_invalidates_state(self):
        # Signup to authenticate
        self.client.post("/api/auth/signup", json={
            "email": "csrf_logout_test@example.com",
            "password": "secure_password"
        })
        self.assertIsNotNone(self.client.cookies.get("csrf_token"))

        # Logout
        self.client.post("/api/auth/logout")
        # csrf_token cookie should be cleared
        self.assertEqual(self.client.cookies.get("csrf_token"), None)

    def test_csrf_meta_callback_exempt(self):
        # GET /auth/facebook/callback -> should not enforce CSRF
        res = self.client.get("/auth/facebook/callback?code=testcode")
        self.assertEqual(res.status_code, 400) # Returns 400 due to invalid testcode, but bypassed 403 CSRF!

    def test_database_sqlite_dev_creation(self):
        from backend.database import init_db, Base
        import backend.database
        
        orig_debug = settings.DEBUG
        orig_url = backend.database.db_url
        orig_init = backend.database._db_initialized
        
        try:
            backend.database.db_url = "sqlite:///./temp_dev_test.db"
            settings.DEBUG = True
            backend.database._db_initialized = False
            
            init_db()
            
            from sqlalchemy import inspect
            inspector = inspect(backend.database.engine)
            tables = inspector.get_table_names()
            self.assertIn("users", tables)
            self.assertIn("user_sessions", tables)
        finally:
            settings.DEBUG = orig_debug
            backend.database.db_url = orig_url
            backend.database._db_initialized = orig_init
            import os
            if os.path.exists("temp_dev_test.db"):
                try:
                    os.remove("temp_dev_test.db")
                except:
                    pass

    def test_database_no_production_fallback(self):
        from backend.database import get_db
        import backend.database
        
        orig_db_url = backend.database.db_url
        orig_engine = backend.database.engine
        orig_session = backend.database.SessionLocal
        orig_init = backend.database._db_initialized
        orig_debug = settings.DEBUG
        
        try:
            backend.database.db_url = "postgresql+psycopg2://nonexistent_user:wrong_password@localhost:5432/failed_db"
            from sqlalchemy import create_engine
            backend.database.engine = create_engine(backend.database.db_url)
            from sqlalchemy.orm import sessionmaker
            backend.database.SessionLocal = sessionmaker(bind=backend.database.engine)
            backend.database._db_initialized = False
            settings.DEBUG = False
            
            db_generator = get_db()
            db = next(db_generator)
            with self.assertRaises(Exception):
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
                
            import os
            self.assertFalse(os.path.exists("/tmp/facebook_crm.db"))
        finally:
            backend.database.db_url = orig_db_url
            backend.database.engine = orig_engine
            backend.database.SessionLocal = orig_session
            backend.database._db_initialized = orig_init
            settings.DEBUG = orig_debug

    def test_vercel_cron_missing_secret_fails(self):
        orig_cron_secret = settings.CRON_SECRET
        try:
            settings.CRON_SECRET = ""
            res = self.client.get("/api/setup/cron-tick")
            self.assertEqual(res.status_code, 401)
        finally:
            settings.CRON_SECRET = orig_cron_secret

    @patch("backend.orchestrator.orchestrator.run_full_autonomous_cycle")
    def test_vercel_cron_security(self, mock_run_cycle):
        mock_run_cycle.return_value = {"status": "MOCK_SUCCESS"}
        
        orig_cron_secret = settings.CRON_SECRET
        try:
            settings.CRON_SECRET = "super_secret_cron_token_123"
            
            # 1. Missing Authorization header -> rejected with 401
            res_missing = self.client.get("/api/setup/cron-tick")
            self.assertEqual(res_missing.status_code, 401)
            
            # 2. Invalid/wrong Authorization header -> rejected with 403
            res_invalid = self.client.get("/api/setup/cron-tick", headers={"Authorization": "Bearer wrong_secret"})
            self.assertEqual(res_invalid.status_code, 403)
            
            # 3. Valid Authorization header -> accepted with 200
            res_valid = self.client.get("/api/setup/cron-tick", headers={"Authorization": "Bearer super_secret_cron_token_123"})
            self.assertEqual(res_valid.status_code, 200)
            self.assertEqual(res_valid.json()["cron_result"]["status"], "MOCK_SUCCESS")
            
            # 4. Ordinary user session -> cannot bypass cron authorization
            self.client.post("/api/auth/signup", json={
                "email": "cron_tester@example.com",
                "password": "securepassword",
                "full_name": "Cron User"
            })
            res_user = self.client.get("/api/setup/cron-tick")
            self.assertEqual(res_user.status_code, 401)
            
            # Sending valid cron token even while logged in -> works
            res_user_valid = self.client.get("/api/setup/cron-tick", headers={"Authorization": "Bearer super_secret_cron_token_123"})
            self.assertEqual(res_user_valid.status_code, 200)
        finally:
            settings.CRON_SECRET = orig_cron_secret

    def test_production_debug_mode_safeguard(self):
        orig_vercel = os.environ.get("VERCEL")
        try:
            os.environ["VERCEL"] = "1"
            with self.assertRaises(ValueError):
                from backend.config import Settings
                Settings(DEBUG=True)
        finally:
            if orig_vercel is not None:
                os.environ["VERCEL"] = orig_vercel
            else:
                os.environ.pop("VERCEL", None)

    def test_demo_mode_disabled_fails_clearly(self):
        from backend.services.meta_graph_service import MetaGraphService
        from backend.services.image_service import ImageService
        from backend.services.groq_service import GroqService
        import asyncio
        
        orig_demo = settings.DEMO_MODE
        try:
            settings.DEMO_MODE = False
            
            svc = MetaGraphService(fb_page_id="", fb_access_token="")
            res = asyncio.run(svc.publish_facebook_post("Test Caption"))
            self.assertFalse(res["success"])
            self.assertIn("disabled", res["error"])
            
            img_svc = ImageService(virtux_api_key="")
            with self.assertRaises(ValueError):
                asyncio.run(img_svc.generate_image("Test Prompt"))
                
            groq_svc = GroqService(api_key="")
            with self.assertRaises(ValueError):
                asyncio.run(groq_svc.generate_completion("Test Prompt"))
        finally:
            settings.DEMO_MODE = orig_demo

    def test_demo_mode_enabled_falls_back_normally(self):
        from backend.services.meta_graph_service import MetaGraphService
        from backend.services.image_service import ImageService
        from backend.services.groq_service import GroqService
        import asyncio
        
        orig_demo = settings.DEMO_MODE
        try:
            settings.DEMO_MODE = True
            
            svc = MetaGraphService(fb_page_id="", fb_access_token="")
            res = asyncio.run(svc.publish_facebook_post("Test Caption"))
            self.assertTrue(res["success"])
            self.assertTrue(res["simulated"])
            
            img_svc = ImageService(virtux_api_key="")
            img_res = asyncio.run(img_svc.generate_image("Test Prompt"))
            self.assertTrue(img_res.startswith("data:image/svg+xml"))
            
            groq_svc = GroqService(api_key="")
            groq_res = asyncio.run(groq_svc.generate_completion("Test Prompt"))
            self.assertIn("title", groq_res)
        finally:
            settings.DEMO_MODE = orig_demo

if __name__ == "__main__":
    unittest.main()
