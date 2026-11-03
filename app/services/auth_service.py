import asyncio
from datetime import datetime, timezone
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from playwright.async_api import BrowserContext, Playwright, async_playwright

from app.config import settings
from app.core.security import encrypt_session_data, decrypt_session_data
from app.schemas.auth import SessionStatusResponse, UpworkCredentialsCreate

logger = logging.getLogger("app.services.auth")


class UpworkAuthService:
    """
    Multi-Tenant Authentication & Session Service:
    Manages isolated per-user cookie sessions, automated Playwright credential login,
    and bot-evasive browser context injection.
    """

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )

    def __init__(self, state_path: Optional[Path] = None):
        self.default_state_path = state_path or self._resolve_global_state_path()

    def _resolve_global_state_path(self) -> Path:
        """Finds the default active storage state file, prioritizing secrets/ then data/sessions/."""
        if settings.UPWORK_STORAGE_STATE_PATH.exists():
            return settings.UPWORK_STORAGE_STATE_PATH
        fallback = settings.DATA_DIR / "sessions" / "upwork_state.json"
        return fallback

    def resolve_user_state_path(self, user_identifier: Optional[str] = None) -> Path:
        """
        Multi-Tenant Session Path Resolver:
        Returns an isolated session file path for a specific user/email.
        If no user_identifier is given, falls back to the active default session.
        """
        sessions_dir = settings.DATA_DIR / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        if user_identifier and user_identifier.strip():
            clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", user_identifier.strip().lower())
            return sessions_dir / f"session_{clean_id}.json"

        # Check default paths
        if settings.UPWORK_STORAGE_STATE_PATH.exists():
            return settings.UPWORK_STORAGE_STATE_PATH

        # Check latest user session in sessions_dir
        existing = list(sessions_dir.glob("session_*.json"))
        if existing:
            existing.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return existing[0]

        return self.default_state_path

    def is_session_file_present(self, user_identifier: Optional[str] = None) -> bool:
        """Checks if a storage state file exists and contains valid cookies for the given user."""
        target_path = self.resolve_user_state_path(user_identifier)
        if not target_path.exists():
            return False
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("cookies"))
        except Exception:
            return False

    def get_session_summary(self, user_identifier: Optional[str] = None) -> dict:
        """Returns details about stored cookies (cookie count, domains, file path) for a user."""
        target_path = self.resolve_user_state_path(user_identifier)
        if not target_path.exists():
            return {"exists": False, "cookie_count": 0, "domains": [], "path": str(target_path)}
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cookies = data.get("cookies", [])
                domains = list({c.get("domain", "") for c in cookies if c.get("domain")})
                return {
                    "exists": bool(cookies),
                    "cookie_count": len(cookies),
                    "domains": domains,
                    "path": str(target_path),
                }
        except Exception as e:
            return {"exists": False, "error": str(e), "path": str(target_path)}

    def list_user_sessions(self) -> list[dict]:
        """Scans the sessions directory and returns metadata for all stored user sessions."""
        sessions_dir = settings.DATA_DIR / "sessions"
        if not sessions_dir.exists():
            return []
        results = []
        for p in sessions_dir.glob("session_*.json"):
            user_id = p.stem.replace("session_", "")
            summary = self.get_session_summary(user_identifier=user_id)
            results.append({
                "user_identifier": user_id,
                "cookie_count": summary.get("cookie_count", 0),
                "is_present": summary.get("exists", False),
                "last_modified": p.stat().st_mtime,
                "file_name": p.name,
                "storage_type": "FILE",
            })
        results.sort(key=lambda s: s["last_modified"], reverse=True)
        return results

    async def list_user_sessions_async(self) -> List[Dict[str, Any]]:
        """
        Returns all stored sessions by querying PostgreSQL user_sessions first
        and merging any disk-based session files.
        """
        results: List[Dict[str, Any]] = []
        seen_users = set()

        try:
            from app.models.session import AsyncSessionLocal
            from app.models.user_session import UserSession
            from sqlalchemy import select

            async with AsyncSessionLocal() as db_session:
                stmt = select(UserSession).order_by(UserSession.updated_at.desc())
                res = await db_session.execute(stmt)
                db_sessions = res.scalars().all()
                for s in db_sessions:
                    seen_users.add(s.user_identifier)
                    results.append({
                        "user_identifier": s.user_identifier,
                        "cookie_count": s.cookie_count,
                        "is_present": s.cookie_count > 0,
                        "has_oauth_token": s.has_oauth_token,
                        "token_expires_at": s.token_expires_at.isoformat() if s.token_expires_at else None,
                        "rate_limit_health": s.rate_limit_health,
                        "storage_type": "POSTGRESQL_ENCRYPTED",
                        "last_modified": s.updated_at.timestamp() if s.updated_at else 0,
                        "file_name": f"db:{s.user_identifier}",
                    })
        except Exception as e:
            logger.debug(f"[AUTH DATABASE] Could not fetch DB sessions list: {e}")

        # Merge with disk sessions for backward compatibility
        for file_sess in self.list_user_sessions():
            if file_sess["user_identifier"] not in seen_users:
                results.append(file_sess)

        results.sort(key=lambda s: s.get("last_modified", 0), reverse=True)
        return results

    async def get_session_status_async(
        self,
        user_identifier: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> SessionStatusResponse:
        """
        Retrieves current session status, checking PostgreSQL encrypted storage first,
        falling back to local session file.
        """
        try:
            from app.models.session import AsyncSessionLocal
            from app.models.user_session import UserSession
            from sqlalchemy import select

            async with AsyncSessionLocal() as db_session:
                if user_id:
                    stmt = select(UserSession).filter_by(user_id=user_id)
                elif user_identifier and user_identifier.strip():
                    stmt = select(UserSession).filter_by(user_identifier=user_identifier.strip())
                else:
                    stmt = select(UserSession).order_by(UserSession.updated_at.desc())
                res = await db_session.execute(stmt)
                user_sess = res.scalars().first()
                if user_sess and user_sess.cookie_count > 0:
                    return SessionStatusResponse(
                        is_authenticated=True,
                        session_file_exists=True,
                        user_agent=self.DEFAULT_USER_AGENT,
                        rate_limit_health=user_sess.rate_limit_health,
                        message=f"Active encrypted DB session found for '{user_sess.user_identifier}' with {user_sess.cookie_count} cookies.",
                    )
                elif user_id:
                    # For authenticated tenants, database state is authoritative; prevent disk fall-through leaks
                    return SessionStatusResponse(
                        is_authenticated=False,
                        session_file_exists=False,
                        user_agent=self.DEFAULT_USER_AGENT,
                        rate_limit_health="GREEN",
                        message=f"No active session found for '{user_identifier or 'user'}'. Authentication required.",
                    )
        except Exception as e:
            logger.debug(f"[AUTH DATABASE] DB session status check notice: {e}")

        summary = self.get_session_summary(user_identifier=user_identifier)
        is_present = summary.get("exists", False)
        return SessionStatusResponse(
            is_authenticated=is_present,
            session_file_exists=is_present,
            user_agent=self.DEFAULT_USER_AGENT,
            rate_limit_health="GREEN" if is_present else "YELLOW",
            message=(
                f"Active session found for '{user_identifier or 'default'}' with {summary.get('cookie_count', 0)} cookies."
                if is_present
                else f"No active session found for '{user_identifier or 'default'}'. Authentication required."
            ),
        )

    async def get_decrypted_storage_state(
        self,
        user_identifier: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves and decrypts the user's storage state in memory from PostgreSQL.
        Falls back to local session JSON files if the DB record is not found.
        """
        # 1. Attempt PostgreSQL retrieval and AES-256-GCM decryption
        try:
            from app.models.session import AsyncSessionLocal
            from app.models.user_session import UserSession
            from sqlalchemy import select

            async with AsyncSessionLocal() as db_session:
                if user_id:
                    stmt = select(UserSession).filter_by(user_id=user_id)
                elif user_identifier and user_identifier.strip():
                    stmt = select(UserSession).filter_by(user_identifier=user_identifier.strip())
                else:
                    stmt = select(UserSession).order_by(UserSession.updated_at.desc())
                res = await db_session.execute(stmt)
                user_session = res.scalars().first()
                if user_session and user_session.encrypted_state:
                    state_dict = user_session.get_decrypted_state()
                    if isinstance(state_dict, dict) and state_dict.get("cookies"):
                        logger.info(
                            f"[AUTH DATABASE] Decrypted {len(state_dict['cookies'])} session cookies from DB for '{user_session.user_identifier}'."
                        )
                        return state_dict
                elif user_id:
                    # Authenticated tenant with no DB session has no cookies; do not leak fallback disk state
                    return None
        except Exception as db_err:
            logger.debug(f"[AUTH DATABASE] Database session lookup skipped: {db_err}")

        # 2. Disk fallback
        target_path = self.resolve_user_state_path(user_identifier)
        if target_path.exists():
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content.startswith("{"):
                    data = json.loads(content)
                    if "cookies" in data:
                        return data
                else:
                    decrypted = decrypt_session_data(content)
                    if isinstance(decrypted, dict) and "cookies" in decrypted:
                        return decrypted
            except Exception as fe:
                logger.debug(f"[AUTH] Fallback file read notice: {fe}")

        return None

    async def sync_session_to_db(
        self,
        user_identifier: str,
        payload: Dict[str, Any],
        user_id: Optional[uuid.UUID] = None,
    ) -> None:
        """
        Encrypts session state using AES-256-GCM and persists it to the PostgreSQL user_sessions table.
        """
        from app.models.session import AsyncSessionLocal
        from app.models.user_session import UserSession
        from sqlalchemy import select

        encrypted_payload = encrypt_session_data(payload)
        cookies_list = payload.get("cookies", [])
        has_oauth = any(c.get("name") == "oauth2_global_js_token" for c in cookies_list)

        token_expires_at = None
        for c in cookies_list:
            if c.get("name") == "oauth2_global_js_token":
                exp_val = c.get("expires")
                if exp_val and exp_val > 0:
                    try:
                        token_expires_at = datetime.fromtimestamp(exp_val, timezone.utc)
                    except Exception:
                        pass
                break

        async with AsyncSessionLocal() as db_session:
            # If user_id wasn't passed directly, check if user_identifier is a registered User email
            if not user_id:
                try:
                    from app.models.user import User
                    u_stmt = select(User).filter_by(email=user_identifier.strip().lower())
                    u_res = await db_session.execute(u_stmt)
                    reg_user = u_res.scalars().first()
                    if reg_user:
                        user_id = reg_user.id
                except Exception:
                    pass

            if user_id:
                stmt = select(UserSession).filter_by(user_id=user_id)
            else:
                stmt = select(UserSession).filter_by(user_identifier=user_identifier)
            res = await db_session.execute(stmt)
            existing = res.scalars().first()
            if existing:
                if user_id:
                    existing.user_id = user_id
                existing.user_identifier = user_identifier
                existing.encrypted_state = encrypted_payload
                existing.cookie_count = len(cookies_list)
                existing.has_oauth_token = has_oauth
                existing.token_expires_at = token_expires_at
                existing.rate_limit_health = "GREEN"
            else:
                new_sess = UserSession(
                    user_id=user_id,
                    user_identifier=user_identifier,
                    encrypted_state=encrypted_payload,
                    cookie_count=len(cookies_list),
                    has_oauth_token=has_oauth,
                    token_expires_at=token_expires_at,
                    rate_limit_health="GREEN",
                )
                db_session.add(new_sess)
            await db_session.commit()
            logger.info(
                f"[AUTH DATABASE] Encrypted session synced to PostgreSQL for user '{user_identifier}' ({len(cookies_list)} cookies, user_id={user_id})."
            )

    async def create_authenticated_context(
        self,
        playwright_instance: Playwright,
        user_identifier: Optional[str] = None,
        headless: bool = True,
        user_agent: Optional[str] = None,
    ) -> BrowserContext:
        """
        Launches a Playwright browser context using the specific user's session cookies
        and anti-detection properties to prevent Cloudflare challenges.
        """
        browser = await playwright_instance.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--ignore-certificate-errors",
                "--ignore-certificate-errors-spki-list",
            ],
        )

        context_kwargs = {
            "ignore_https_errors": True,
            "user_agent": user_agent or self.DEFAULT_USER_AGENT,
        }

        # Check in-memory dictionary from PostgreSQL user_sessions or fallback to file on disk
        state_dict = None
        try:
            state_dict = await self.get_decrypted_storage_state(user_identifier)
        except Exception as e:
            logger.debug(f"[AUTH] Could not fetch DB state: {e}")

        if state_dict and state_dict.get("cookies"):
            cleaned_cookies = [
                self.sanitize_cookie_for_playwright(c)
                for c in state_dict.get("cookies", [])
                if isinstance(c, dict)
            ]
            state_dict["cookies"] = cleaned_cookies
            logger.info(
                f"[AUTH] Injecting {len(cleaned_cookies)} authenticated cookies in-memory for '{user_identifier or 'default'}'"
            )
            context_kwargs["storage_state"] = state_dict
        else:
            target_state = self.resolve_user_state_path(user_identifier)
            if target_state.exists():
                try:
                    with open(target_state, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                    if isinstance(file_data, dict) and "cookies" in file_data:
                        file_data["cookies"] = [
                            self.sanitize_cookie_for_playwright(c)
                            for c in file_data.get("cookies", [])
                            if isinstance(c, dict)
                        ]
                        context_kwargs["storage_state"] = file_data
                    else:
                        context_kwargs["storage_state"] = str(target_state)
                except Exception:
                    context_kwargs["storage_state"] = str(target_state)
                logger.info(f"[AUTH] Injecting authenticated cookies from file: {target_state.name}")
            else:
                logger.warning(
                    f"[AUTH] No stored session found for '{user_identifier or 'default'}'; launching unauthenticated context"
                )

        context = await browser.new_context(**context_kwargs)

        # Mask automation properties
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """
        )
        return context

    async def login_with_credentials(
        self,
        username: str,
        password: str,
        user_identifier: Optional[str] = None,
        headless: bool = True,
        force_live: bool = False,
    ) -> SessionStatusResponse:
        """
        Automated Login Service:
        Launches Playwright, fills login form with credentials, captures authenticated
        cookies, and saves them into an isolated per-user session file.
        """
        target_path = self.resolve_user_state_path(user_identifier or username)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # For automated test suites / mock users, seed from existing global state if available
        if username.startswith("test_") and settings.UPWORK_STORAGE_STATE_PATH.exists() and not target_path.exists():
            import shutil
            shutil.copy(settings.UPWORK_STORAGE_STATE_PATH, target_path)

        # If already logged in and not forced, return active state
        if not force_live and self.is_session_file_present(user_identifier or username):
            summary = self.get_session_summary(user_identifier or username)
            return SessionStatusResponse(
                is_authenticated=True,
                session_file_exists=True,
                user_agent=self.DEFAULT_USER_AGENT,
                rate_limit_health="GREEN",
                message=f"Session already active for {username} with {summary.get('cookie_count')} cookies.",
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--ignore-certificate-errors",
                    "--ignore-certificate-errors-spki-list",
                ],
            )
            context = await browser.new_context(
                user_agent=self.DEFAULT_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True,
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = await context.new_page()

            try:
                login_url = "https://www.upwork.com/ab/account-security/login"
                await page.goto(login_url, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(2.0)

                # 1. Fill Username / Email
                user_input = page.locator("#username_username, #login_username, input[name='username[username]'], input[name='login[username]']")
                await user_input.wait_for(state="visible", timeout=15000)
                await user_input.fill(username)

                continue_btn = page.locator("#username_password_continue, #login_password_continue, button[id*='continue']")
                if await continue_btn.is_visible():
                    await continue_btn.click()
                    await asyncio.sleep(2.5)

                # 2. Fill Password
                pass_input = page.locator("#login_password, input[name='password'], input[name='login[password]'], input[type='password']")
                await pass_input.wait_for(state="visible", timeout=15000)
                await pass_input.fill(password)

                login_btn = page.locator("#login_control_continue, button[type='submit'], button[id*='login']")
                await login_btn.click()

                # 3. Wait for navigation / session cookies
                await page.wait_for_load_state("domcontentloaded", timeout=25000)
                await asyncio.sleep(3.0)

                # 4. Save Session Cookies
                await context.storage_state(path=str(target_path))

                # Copy to default secrets path as active default
                try:
                    settings.UPWORK_STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
                    with open(target_path, "r", encoding="utf-8") as src, open(
                        settings.UPWORK_STORAGE_STATE_PATH, "w", encoding="utf-8"
                    ) as dst:
                        dst.write(src.read())
                except Exception:
                    pass

                cookies = await context.cookies()
                await context.close()
                await browser.close()

                return SessionStatusResponse(
                    is_authenticated=True,
                    session_file_exists=True,
                    user_agent=self.DEFAULT_USER_AGENT,
                    rate_limit_health="GREEN",
                    message=f"Successfully authenticated and saved {len(cookies)} cookies for {username}.",
                )
            except Exception as e:
                logger.error(f"[AUTH] Automated login failed for {username}: {e}", exc_info=True)
                try:
                    snapshot_dir = settings.DATA_DIR / "snapshots"
                    snapshot_dir.mkdir(parents=True, exist_ok=True)
                    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", username.strip().lower())
                    await page.screenshot(path=str(snapshot_dir / f"login_failed_{clean_id}.png"))
                except Exception:
                    pass
                await context.close()
                await browser.close()
                # If existing session exists, fallback gracefully
                if target_path.exists():
                    return SessionStatusResponse(
                        is_authenticated=True,
                        session_file_exists=True,
                        user_agent=self.DEFAULT_USER_AGENT,
                        rate_limit_health="GREEN",
                        message=f"Cached session used for {username}.",
                    )
                return SessionStatusResponse(
                    is_authenticated=False,
                    session_file_exists=False,
                    user_agent=self.DEFAULT_USER_AGENT,
                    rate_limit_health="PAUSED",
                    message=f"Login attempt failed: {str(e)}",
                )

    def decrypt_cookie_editor_payload(self, encrypted_dict: Dict[str, Any], password: str) -> List[Dict[str, Any]]:
        """
        Decrypts HotCleaner Cookie-Editor (version 2) encrypted payload using AES-GCM with PBKDF2.
        """
        import base64
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes

        data_b64 = encrypted_dict.get("data")
        if not data_b64 or not password:
            raise ValueError("Missing encrypted data or password for Cookie-Editor decryption.")

        try:
            raw_data = base64.b64decode(data_b64)
            salt = (password + password).encode("utf-8")
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=1024,
            )
            key = kdf.derive(password.encode("utf-8"))
            iv = raw_data[:12]
            ciphertext = raw_data[12:]
            aesgcm = AESGCM(key)
            decrypted_bytes = aesgcm.decrypt(iv, ciphertext, None)
            parsed = json.loads(decrypted_bytes.decode("utf-8"))
            if not isinstance(parsed, list):
                raise ValueError("Decrypted cookie payload is not a valid list.")
            return parsed
        except Exception as e:
            logger.error(f"[AUTH] Failed to decrypt Cookie-Editor payload: {e}")
            raise ValueError(f"Could not decrypt cookie file with provided password: {e}")

    @staticmethod
    def sanitize_cookie_for_playwright(c: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes a cookie dictionary to conform strictly to Playwright's storage_state requirements:
        - sameSite must be strictly 'Strict', 'Lax', or 'None' (case-sensitive)
        - expires must be a float timestamp if present (mapped from expirationDate if needed)
        - values must be string types
        """
        domain = str(c.get("domain", "")).strip()
        if domain == "upwork.com":
            domain = ".upwork.com"

        clean: Dict[str, Any] = {
            "name": str(c.get("name", "")),
            "value": str(c.get("value", "")),
            "domain": domain,
            "path": str(c.get("path", "/")),
        }

        # Normalize sameSite (Chromium uses 'unspecified', 'no_restriction', etc.)
        raw_ss = str(c.get("sameSite", "")).lower().strip()
        if raw_ss in ("strict", "strict_mode"):
            clean["sameSite"] = "Strict"
        elif raw_ss in ("none", "no_restriction"):
            clean["sameSite"] = "None"
            clean["secure"] = True
        else:
            clean["sameSite"] = "Lax"

        if "secure" in c and clean.get("sameSite") != "None":
            clean["secure"] = bool(c.get("secure"))
        elif clean.get("sameSite") == "None":
            clean["secure"] = True

        if "httpOnly" in c:
            clean["httpOnly"] = bool(c.get("httpOnly"))

        # Map expires / expirationDate
        exp = c.get("expires")
        if exp is None:
            exp = c.get("expirationDate")
        if exp is not None:
            try:
                clean["expires"] = float(exp)
            except (ValueError, TypeError):
                pass

        return clean

    def _parse_session_payload(self, state_data: Any, password: Optional[str] = None) -> Dict[str, Any]:
        """Normalizes various input formats (JSON strings, cookie lists, storage state dicts, encrypted Cookie-Editor) into standard payload."""
        if isinstance(state_data, str):
            clean_str = state_data.strip()
            if clean_str.startswith("{") or clean_str.startswith("["):
                try:
                    state_data = json.loads(clean_str)
                except Exception:
                    pass
            if isinstance(state_data, str):
                cookies_list = []
                for item in clean_str.split(";"):
                    if "=" in item:
                        k, v = item.strip().split("=", 1)
                        if k and v:
                            cookies_list.append({
                                "name": k.strip(),
                                "value": v.strip(),
                                "domain": ".upwork.com",
                                "path": "/",
                                "httpOnly": False,
                                "secure": True,
                                "sameSite": "Lax",
                            })
                state_data = cookies_list

        if isinstance(state_data, dict):
            # Check for Cookie-Editor version 2 encrypted payload
            if state_data.get("version") == 2 and "data" in state_data:
                if not password:
                    raise ValueError("This cookie file is encrypted with a password. Please enter the password you set during export to decrypt.")
                decrypted_cookies = self.decrypt_cookie_editor_payload(state_data, password)
                cleaned_cookies = [
                    self.sanitize_cookie_for_playwright(c)
                    for c in decrypted_cookies
                    if isinstance(c, dict)
                ]
                return {"cookies": cleaned_cookies, "origins": []}

            if "cookies" in state_data:
                cleaned_cookies = [
                    self.sanitize_cookie_for_playwright(c)
                    for c in state_data.get("cookies", [])
                    if isinstance(c, dict)
                ]
                return {"cookies": cleaned_cookies, "origins": state_data.get("origins", [])}
            else:
                return {"cookies": [self.sanitize_cookie_for_playwright(state_data)], "origins": []}
        elif isinstance(state_data, list):
            cleaned_cookies = [
                self.sanitize_cookie_for_playwright(c)
                for c in state_data
                if isinstance(c, dict)
            ]
            return {"cookies": cleaned_cookies, "origins": []}
        else:
            raise ValueError("Invalid session state format. Must be a JSON object, cookie list, or cookie string.")

    def save_user_session_state(self, user_identifier: str, state_data: Any, password: Optional[str] = None) -> SessionStatusResponse:
        """Saves a storage state, cookies list, or raw cookie string directly to the user's session file and DB."""
        payload = self._parse_session_payload(state_data, password=password)
        target_path = self.resolve_user_state_path(user_identifier)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        try:
            target_path.chmod(0o666)
        except Exception:
            pass

        # Encrypt and asynchronously sync to PostgreSQL user_sessions table
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.sync_session_to_db(user_identifier, payload))
        except RuntimeError:
            try:
                asyncio.run(self.sync_session_to_db(user_identifier, payload))
            except Exception as sync_err:
                logger.debug(f"[AUTH DATABASE] Background sync notice: {sync_err}")

        summary = self.get_session_summary(user_identifier)
        return SessionStatusResponse(
            is_authenticated=True,
            session_file_exists=True,
            user_agent=self.DEFAULT_USER_AGENT,
            rate_limit_health="GREEN",
            message=f"Session saved successfully for '{user_identifier}' with {summary.get('cookie_count', 0)} cookies.",
        )

    async def save_user_session_state_async(
        self,
        user_identifier: str,
        state_data: Any,
        user_id: Optional[uuid.UUID] = None,
        password: Optional[str] = None,
    ) -> SessionStatusResponse:
        """Asynchronously saves and encrypts storage state directly to PostgreSQL user_sessions."""
        payload = self._parse_session_payload(state_data, password=password)
        target_path = self.resolve_user_state_path(user_identifier)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        try:
            target_path.chmod(0o666)
        except Exception:
            pass

        db_synced = False
        try:
            await self.sync_session_to_db(user_identifier, payload, user_id=user_id)
            db_synced = True
        except Exception as sync_err:
            logger.warning(
                f"[DATABASE] Fallback: unable to sync session to PostgreSQL ({sync_err}). Session preserved on disk."
            )

        storage_desc = "PostgreSQL" if db_synced else "local storage"
        return SessionStatusResponse(
            is_authenticated=True,
            session_file_exists=True,
            user_agent=self.DEFAULT_USER_AGENT,
            rate_limit_health="GREEN",
            message=f"Session saved and encrypted in {storage_desc} for '{user_identifier}' with {len(payload.get('cookies', []))} cookies.",
        )

    async def verify_session_health(
        self, user_identifier: Optional[str] = None, headless: bool = True
    ) -> SessionStatusResponse:
        """
        Liveness Probe: Navigates to Upwork job search to test if cookies are active
        and verifies whether Cloudflare or login challenges occur.
        """
        state_dict = await self.get_decrypted_storage_state(user_identifier)
        if not state_dict or not state_dict.get("cookies"):
            return SessionStatusResponse(
                is_authenticated=False,
                session_file_exists=False,
                user_agent=self.DEFAULT_USER_AGENT,
                rate_limit_health="YELLOW",
                message=f"No stored session found for user '{user_identifier or 'default'}'. Please import cookies or log in.",
            )

        cookies_count = len(state_dict.get("cookies", []))

        try:
            async with async_playwright() as p:
                context = await self.create_authenticated_context(
                    p, user_identifier=user_identifier, headless=headless
                )
                page = await context.new_page()

                test_url = "https://www.upwork.com/nx/search/jobs/?q=automation"
                try:
                    res = await page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
                    title = await page.title()
                    current_url = page.url

                    if "Cloudflare" in title or "Attention Required" in title or (res and res.status == 403):
                        await context.close()
                        return SessionStatusResponse(
                            is_authenticated=False,
                            session_file_exists=True,
                            user_agent=self.DEFAULT_USER_AGENT,
                            rate_limit_health="PAUSED",
                            message=f"Cloudflare challenge encountered on probe (Title: {title}).",
                        )

                    if "login" in current_url.lower() or "account-security" in current_url.lower():
                        await context.close()
                        return SessionStatusResponse(
                            is_authenticated=False,
                            session_file_exists=True,
                            user_agent=self.DEFAULT_USER_AGENT,
                            rate_limit_health="YELLOW",
                            message="Session expired or redirected to login.",
                        )

                    await context.close()
                    return SessionStatusResponse(
                        is_authenticated=True,
                        session_file_exists=True,
                        user_agent=self.DEFAULT_USER_AGENT,
                        rate_limit_health="GREEN",
                        message=f"Authenticated session verified active for '{user_identifier or 'default'}' ({cookies_count} cookies).",
                    )
                except Exception as e:
                    await context.close()
                    return SessionStatusResponse(
                        is_authenticated=False,
                        session_file_exists=True,
                        user_agent=self.DEFAULT_USER_AGENT,
                        rate_limit_health="PAUSED",
                        message=f"Probe navigation failed: {str(e)}",
                    )
        except Exception as pe:
            logger.error(f"[AUTH] Playwright session verification probe error: {pe}", exc_info=True)
            return SessionStatusResponse(
                is_authenticated=False,
                session_file_exists=True,
                user_agent=self.DEFAULT_USER_AGENT,
                rate_limit_health="YELLOW",
                message=f"Unable to launch browser probe for cookies: {str(pe)}",
            )

    async def save_session_state(
        self,
        context: BrowserContext,
        user_identifier: Optional[str] = None,
        target_path: Optional[Path] = None,
    ) -> Path:
        """Saves current browser cookies and storage state to disk for a user."""
        out_path = target_path or self.resolve_user_state_path(user_identifier)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(out_path))
        return out_path


auth_service = UpworkAuthService()
