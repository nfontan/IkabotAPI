import logging
import os
import random
import threading
import requests

from playwright.sync_api import sync_playwright

import settings

logger = logging.getLogger(__name__)


# In-memory cache for IP -> timezone mapping to avoid hitting external API rate limits and add zero latency for cached IPs
IP_TIMEZONE_CACHE = {}


def get_timezone_from_ip(ip: str) -> str:
    """
    Resolve the IANA timezone ID from a public IP address.
    Uses in-memory caching and fast timeouts with fallbacks.
    """
    default_timezone = 'Europe/London'
    
    if not ip or ip in ("127.0.0.1", "localhost", "::1") or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16."):
        return default_timezone
    
    if ip in IP_TIMEZONE_CACHE:
        return IP_TIMEZONE_CACHE[ip]
    
    # Try ip-api.com (free, fast, no API key needed, limit 45 req/min)
    try:
        url = f"http://ip-api.com/json/{ip}"
        response = requests.get(url, timeout=1.5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and "timezone" in data:
                tz = data["timezone"]
                IP_TIMEZONE_CACHE[ip] = tz
                logger.info(f"Resolved timezone '{tz}' for IP {ip} via ip-api.com")
                return tz
    except Exception as e:
        logger.warning(f"Failed to resolve timezone for IP {ip} using ip-api.com: {e}")
        
    # Fallback to ipapi.co if ip-api.com fails
    try:
        url = f"https://ipapi.co/{ip}/timezone/"
        response = requests.get(url, timeout=1.5)
        if response.status_code == 200:
            tz = response.text.strip()
            if tz and "/" in tz and " " not in tz:
                IP_TIMEZONE_CACHE[ip] = tz
                logger.info(f"Resolved timezone '{tz}' for IP {ip} via ipapi.co")
                return tz
    except Exception as e:
        logger.warning(f"Failed to resolve timezone for IP {ip} using ipapi.co: {e}")

    # Fallback to default if all lookups fail
    logger.warning(f"Could not resolve timezone for IP {ip}, falling back to default '{default_timezone}'")
    return default_timezone


class TokenGenerator:
    """
    TokenGenerator class for generating tokens using Playwright.

    Uses a threading lock to prevent concurrent Playwright subprocess spawning
    (which causes "Racing with another loop" crashes with uvloop). Each call
    generates a fresh blackbox token.

    Usage:
    ```
    token_generator = TokenGenerator(supported_user_agents=["User Agent 1", "User Agent 2"])
    token = token_generator.get_token()
    ```
    """

    def __init__(self, supported_user_agents):
        """
        Initialize TokenGenerator.

        Args:
        - supported_user_agents: List of supported user agent strings.
        """
        current_directory = os.path.dirname(os.path.abspath(__file__))
        self.html_file_path = f"file:///{current_directory}/token.html"
        self.supported_user_agents = supported_user_agents
        self._lock = threading.Lock()

    def get_token(self, user_agent: str = None, timezone_id: str = None):
        """
        Generate a fresh blackbox token.

        A threading lock serializes Playwright calls to prevent uvloop race
        conditions when multiple requests arrive concurrently. When no
        user_agent is provided, a random one from the supported list is used.

        Args:
        - user_agent (str, optional): The user agent string to use for the browser.
        - timezone_id (str, optional): The IANA timezone ID to use for the browser context.

        Returns:
        - str: The generated token.
        """
        effective_ua = user_agent if user_agent else random.choice(self.supported_user_agents)

        with self._lock:
            return self._generate_token(effective_ua, timezone_id)

    def _generate_token(self, user_agent: str, timezone_id: str = None):
        """
        Launch Playwright to generate a fresh token.

        Args:
        - user_agent (str): The user agent string to use for the browser.
        - timezone_id (str, optional): The IANA timezone ID to use for the browser context.

        Returns:
        - str: The generated token.
        """
        effective_tz = timezone_id if timezone_id else 'Europe/London'
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=settings.PLAYWRIGHT_HEADLESS,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            context = browser.new_context(
                user_agent=user_agent,
                timezone_id=effective_tz,
            )
            page = context.new_page()
            page.goto(self.html_file_path)
            token_element = page.wait_for_selector("body > div")
            token = token_element.inner_text()
            browser.close()
        return token
