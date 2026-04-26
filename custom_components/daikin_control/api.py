"""API client for Daikin Control Cloud Services."""
import asyncio
import logging
import time

import aiohttp

from .const import BASE_URL, LOGIN_URL, PARAMETER_URL

INFO_URL = f"{BASE_URL}/installation/info"

_LOGGER = logging.getLogger(__name__)

REST_API_URL = "https://api.rotex-control.com"

# Request timeouts: total 30 seconds, 10s connect
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10)

# Retry config for transient errors
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries


class DaikinControlApiError(Exception):
    """API error."""


class DaikinControlTransientError(DaikinControlApiError):
    """Transient API error (timeout, network issue) - last value should be kept."""


class DaikinControlApi:
    """API client for daikin-control.com."""

    def __init__(self, username: str, password: str, installation_id: str) -> None:
        self._username = username
        self._password = password
        self._installation_id = installation_id
        self._session: aiohttp.ClientSession | None = None
        self._logged_in = False
        self._login_time: float = 0
        self._session_max_age: int = 5 * 3600  # Refresh before 6h expiry

    async def _close_and_reset_session(self) -> None:
        """Close existing session to force a fresh one on next login."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self._logged_in = False

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            jar = aiohttp.CookieJar(unsafe=True)
            self._session = aiohttp.ClientSession(
                cookie_jar=jar, timeout=REQUEST_TIMEOUT
            )
            self._logged_in = False
        return self._session

    async def login(self) -> bool:
        """Login via two-step process: REST API login, then form login."""
        session = await self._ensure_session()
        try:
            # Step 1: REST API login (api.rotex-control.com)
            _LOGGER.debug("Daikin Control: Step 1 - REST API login")
            try:
                async with session.post(
                    f"{REST_API_URL}/login",
                    json={
                        "username": self._username,
                        "password": self._password,
                    },
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "HomeAssistant/DaikinControl",
                    },
                    ssl=True,
                ) as resp:
                    _LOGGER.debug("REST API login response: %s", resp.status)
            except Exception as err:
                _LOGGER.debug("REST API login skipped/failed: %s", err)

            # Step 2: Form login (daikin-control.com/login_check)
            _LOGGER.debug("Daikin Control: Step 2 - Form login")
            async with session.post(
                LOGIN_URL,
                data={
                    "_username": self._username,
                    "_password": self._password,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Mozilla/5.0 (compatible; HomeAssistant/DaikinControl)",
                    "Referer": f"{BASE_URL}/login",
                },
                allow_redirects=False,
                ssl=True,
            ) as resp:
                _LOGGER.debug(
                    "Form login response: status=%s",
                    resp.status,
                )

                # 302 = successful login with redirect
                if resp.status == 302:
                    cookies = session.cookie_jar.filter_cookies(BASE_URL)
                    if "PHPSESSID" in cookies:
                        self._logged_in = True
                        self._login_time = time.time()
                        _LOGGER.info("Daikin Control login successful")
                        return True

                # 200 = login page shown again = wrong credentials
                if resp.status == 200:
                    _LOGGER.error("Daikin Control login failed: wrong credentials (got login page back)")
                    return False

                _LOGGER.error("Daikin Control login failed: unexpected status %s", resp.status)
                return False

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Daikin Control login error: %s", err)
            return False

    async def _login_with_retry(self) -> bool:
        """Login with automatic retries for transient errors."""
        for attempt in range(1, MAX_RETRIES + 1):
            if await self.login():
                return True
            if attempt < MAX_RETRIES:
                _LOGGER.info(
                    "Login attempt %d/%d failed, retrying in %ds",
                    attempt, MAX_RETRIES, RETRY_DELAY,
                )
                await asyncio.sleep(RETRY_DELAY)
        return False

    async def _fetch_parameters_raw(self, limit: int) -> list[dict]:
        """Single attempt to fetch parameters."""
        session = await self._ensure_session()
        if not self._logged_in:
            if not await self._login_with_retry():
                raise DaikinControlTransientError("Login failed after retries")

        url = (
            f"{PARAMETER_URL}?filter[installation]={self._installation_id}"
            f"&offset=0&limit={limit}"
        )

        try:
            async with session.get(
                url,
                headers={
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": "Mozilla/5.0 (compatible; HomeAssistant/DaikinControl)",
                },
                allow_redirects=False,
                ssl=True,
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if text.strip().startswith("{"):
                        import json
                        data = json.loads(text)
                        return data.get("models", [])
                    _LOGGER.info("Got HTML instead of JSON, session expired")
                    self._logged_in = False
                    await self._close_and_reset_session()
                    if await self._login_with_retry():
                        return await self._fetch_parameters_raw(limit)
                    raise DaikinControlTransientError("Re-login failed")
                if resp.status in (301, 302, 401, 403):
                    _LOGGER.info("Session expired (status %s), re-logging in", resp.status)
                    self._logged_in = False
                    await self._close_and_reset_session()
                    if await self._login_with_retry():
                        return await self._fetch_parameters_raw(limit)
                    raise DaikinControlTransientError("Re-login failed")
                raise DaikinControlApiError(f"API error: {resp.status}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            self._logged_in = False
            raise DaikinControlTransientError(f"Request error: {err}") from err

    async def get_parameters(self, limit: int = 100) -> list[dict]:
        # Proactively refresh session before it expires
        if self._logged_in and (time.time() - self._login_time) > self._session_max_age:
            _LOGGER.info("Session approaching expiry, proactively refreshing")
            await self._close_and_reset_session()

        last_err: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await self._fetch_parameters_raw(limit)
            except DaikinControlTransientError as err:
                last_err = err
                if attempt < MAX_RETRIES:
                    _LOGGER.info(
                        "Transient error on attempt %d/%d: %s - retrying in %ds",
                        attempt, MAX_RETRIES, err, RETRY_DELAY,
                    )
                    await asyncio.sleep(RETRY_DELAY)
            except DaikinControlApiError as err:
                # Non-transient error, don't retry
                raise
        assert last_err is not None
        raise last_err

    async def _fetch_installation_info_raw(self) -> dict:
        """Single attempt to fetch installation info (gateway status)."""
        session = await self._ensure_session()
        if not self._logged_in:
            if not await self._login_with_retry():
                raise DaikinControlTransientError("Login failed after retries")

        url = f"{INFO_URL}/{self._installation_id}"

        try:
            async with session.get(
                url,
                headers={
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": "Mozilla/5.0 (compatible; HomeAssistant/DaikinControl)",
                },
                allow_redirects=False,
                ssl=True,
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if text.strip().startswith("{"):
                        import json
                        return json.loads(text)
                    _LOGGER.info("Info endpoint returned HTML, session expired")
                    self._logged_in = False
                    await self._close_and_reset_session()
                    if await self._login_with_retry():
                        return await self._fetch_installation_info_raw()
                    raise DaikinControlTransientError("Re-login failed")
                if resp.status in (301, 302, 401, 403):
                    self._logged_in = False
                    await self._close_and_reset_session()
                    if await self._login_with_retry():
                        return await self._fetch_installation_info_raw()
                    raise DaikinControlTransientError("Re-login failed")
                raise DaikinControlApiError(f"Info API error: {resp.status}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            self._logged_in = False
            raise DaikinControlTransientError(f"Info request error: {err}") from err

    async def get_installation_info(self) -> dict:
        """Get installation info with retries.

        Returns dict like:
        {
            "installationId": "...",
            "lastCanBusContact": <timestamp>,
            "latestGatewayContact": <timestamp>,
            "activeWithinLastHour": <bool>,
            "swVersion": "..."
        }
        """
        if self._logged_in and (time.time() - self._login_time) > self._session_max_age:
            await self._close_and_reset_session()

        last_err: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await self._fetch_installation_info_raw()
            except DaikinControlTransientError as err:
                last_err = err
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
            except DaikinControlApiError:
                raise
        assert last_err is not None
        raise last_err

    async def get_latest_values(self) -> dict[str, dict]:
        """Fetch parameters and return latest value per parameter+device combo."""
        models = await self.get_parameters(limit=200)

        latest: dict[str, dict] = {}
        for entry in models:
            name = entry.get("name", "")
            device_name = entry.get("device", {}).get("name", "")
            device_type = entry.get("device", {}).get("type", "")
            key = f"{device_name}_{name}"

            ts = entry.get("date", 0)
            if key not in latest or ts > latest[key].get("date", 0):
                latest[key] = {
                    "name": name,
                    "device_name": device_name,
                    "device_type": device_type,
                    "date": ts,
                    "value": entry.get("value", ""),
                    "display": entry.get("display", False),
                }
        return latest

    async def test_connection(self) -> bool:
        try:
            if await self._login_with_retry():
                params = await self.get_parameters(limit=1)
                return len(params) > 0
        except DaikinControlApiError:
            pass
        return False

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
