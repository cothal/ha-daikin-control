"""API client for Daikin Control Cloud Services."""
import logging

import aiohttp

from .const import BASE_URL, LOGIN_URL, PARAMETER_URL

_LOGGER = logging.getLogger(__name__)

REST_API_URL = "https://api.rotex-control.com"


class DaikinControlApiError(Exception):
    """API error."""


class DaikinControlApi:
    """API client for daikin-control.com."""

    def __init__(self, username: str, password: str, installation_id: str) -> None:
        self._username = username
        self._password = password
        self._installation_id = installation_id
        self._session: aiohttp.ClientSession | None = None
        self._logged_in = False

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            jar = aiohttp.CookieJar(unsafe=True)
            self._session = aiohttp.ClientSession(cookie_jar=jar)
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
            # Do NOT follow redirects - we just need the Set-Cookie header
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
                    "Form login response: status=%s headers=%s",
                    resp.status,
                    dict(resp.headers),
                )

                # 302 = successful login with redirect
                if resp.status == 302:
                    cookies = session.cookie_jar.filter_cookies(BASE_URL)
                    _LOGGER.debug("Cookies after login: %s", list(cookies.keys()))
                    if "PHPSESSID" in cookies:
                        self._logged_in = True
                        _LOGGER.info("Daikin Control login successful")
                        return True

                # 200 = login page shown again = wrong credentials
                if resp.status == 200:
                    _LOGGER.error("Daikin Control login failed: wrong credentials (got login page back)")
                    return False

                _LOGGER.error("Daikin Control login failed: unexpected status %s", resp.status)
                return False

        except aiohttp.ClientError as err:
            _LOGGER.error("Daikin Control login error: %s", err)
            return False

    async def get_parameters(self, limit: int = 100) -> list[dict]:
        session = await self._ensure_session()
        if not self._logged_in:
            if not await self.login():
                raise DaikinControlApiError("Login failed")

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
                    # Check if we got JSON or HTML (login page)
                    if text.strip().startswith("{"):
                        import json
                        data = json.loads(text)
                        return data.get("models", [])
                    else:
                        _LOGGER.info("Got HTML instead of JSON, session expired")
                        self._logged_in = False
                        if await self.login():
                            return await self.get_parameters(limit)
                        raise DaikinControlApiError("Re-login failed")
                elif resp.status in (302, 301):
                    _LOGGER.info("Session expired (redirect), re-logging in")
                    self._logged_in = False
                    if await self.login():
                        return await self.get_parameters(limit)
                    raise DaikinControlApiError("Re-login failed")
                else:
                    raise DaikinControlApiError(f"API error: {resp.status}")
        except aiohttp.ClientError as err:
            self._logged_in = False
            raise DaikinControlApiError(f"Request error: {err}") from err

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
            if await self.login():
                params = await self.get_parameters(limit=1)
                return len(params) > 0
        except DaikinControlApiError:
            pass
        return False

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
