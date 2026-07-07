import logging
import os
import random
import threading

from playwright.sync_api import sync_playwright

import settings

logger = logging.getLogger(__name__)


class TokenGenerator:

    def __init__(self, supported_user_agents):
        self.token_page_url = "http://localhost:5005/v1/token-page"
        self.supported_user_agents = supported_user_agents
        self._lock = threading.Lock()
        self._stealth_script = self._build_stealth_script()

    def _build_stealth_script(self):
        return """
     Object.defineProperty(navigator, 'webdriver', {
         get: () => undefined, configurable: true,
     });

     window.chrome = {
         runtime: {
             connect: () => ({ onMessage: { addListener: () => {} }, onDisconnect: { addListener: () => {} }, postMessage: () => {} }),
             sendMessage: () => {}, onMessage: { addListener: () => {} }, onConnect: { addListener: () => {} },
         },
         loadTimes: () => ({}),
         csi: () => ({}),
         app: { isInstalled: false },
         webstore: {},
         runtime: {},
     };

     Object.defineProperty(navigator, 'plugins', {
         get: () => { const p = [ { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' } ]; p.item = (i) => p[i]; p.namedItem = (n) => null; p.refresh = () => {}; return p; },
         configurable: true,
     });

     Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en-US', 'en'], configurable: true });
     Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8, configurable: true });
     Object.defineProperty(navigator, 'deviceMemory', { get: () => 8, configurable: true });
     Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0, configurable: true });
     Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.', configurable: true });
     Object.defineProperty(navigator, 'platform', { get: () => 'Win32', configurable: true });

     ['cdc_adoQpoasnfa76pfcZLmcfl_', '__pw_manual', '__playwright', 'playwright', '__puppeteer', 'puppeteer', '__selenium_evaluate', 'selenium', '__webdriver_evaluate', '__fxdriver_evaluate', '__driver_evaluate', '__webdriver_script_function', '__webdriver_unwrapped', '__driver_unwrapped', '__selenium_unwrapped', '__fxdriver_unwrapped', '_phantom', 'phantom', 'callPhantom', 'domAutomation', 'domAutomationController', '__puppeteer_evaluation_script__'].forEach(k => { try { if (k in window) delete window[k]; } catch(e) {} });

     try { Object.defineProperty(window, '$cdc_asdjflasutopfhvcZLmcfl_', { get: () => undefined, set: () => {}, configurable: false }); } catch(e) {}
     Object.defineProperty(document, '__webdriver_script_fn', { get: () => undefined, configurable: true });

     const _t = Function.prototype.toString;
     Function.prototype.toString = function() { const s = _t.call(this); if (s.includes('[native code]') || this === Function.prototype.toString) return 'function toString() { [native code] }'; return s; };
"""

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
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            context = browser.new_context(
                user_agent=user_agent,
                locale='es-ES',
                timezone_id='America/Argentina/Buenos_Aires',
            )
            context.add_init_script(self._stealth_script)
            page = context.new_page()
            logger.info(f"Navigating to {self.token_page_url}")
            page.goto(self.token_page_url, wait_until='networkidle')
            logger.info("Page loaded, waiting for token")
            token_element = page.wait_for_selector("body > div", timeout=30000)
            token = token_element.inner_text()
            if not token:
                raise Exception("Empty token received")
            logger.info(f"Token length: {len(token)}")
            browser.close()
        return token
