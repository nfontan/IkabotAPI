import logging
import os
import random
import threading

from playwright.sync_api import sync_playwright

import settings

logger = logging.getLogger(__name__)


class TokenGenerator:

    def __init__(self, supported_user_agents):
        current_directory = os.path.dirname(os.path.abspath(__file__))
        self.html_file_path = f"file:///{current_directory}/token.html"
        self.supported_user_agents = supported_user_agents
        self._lock = threading.Lock()

    def get_token(self, user_agent: str = None):
        effective_ua = user_agent if user_agent else random.choice(self.supported_user_agents)
        with self._lock:
            return self._generate_token(effective_ua)

    def _generate_token(self, user_agent: str):
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
                locale='es-ES',
                timezone_id='America/Argentina/Buenos_Aires',
            )
            page = context.new_page()
            page.goto(self.html_file_path)
            token_element = page.wait_for_selector("body > div")
            token = token_element.inner_text()
            browser.close()
        return token
