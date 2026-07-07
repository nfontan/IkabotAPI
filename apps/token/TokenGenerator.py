import logging
import os
import random
import threading

from playwright.sync_api import sync_playwright

import settings

logger = logging.getLogger(__name__)


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
        self._stealth_script = self._build_stealth_script()

    def _build_stealth_script(self):
        return """
     Object.defineProperty(navigator, 'webdriver', {
         get: () => undefined,
         configurable: true,
     });

     window.chrome = {
         runtime: {
             connect: () => ({
                 onMessage: { addListener: () => {} },
                 onDisconnect: { addListener: () => {} },
                 postMessage: () => {},
             }),
             sendMessage: () => {},
             onMessage: { addListener: () => {} },
             onConnect: { addListener: () => {} },
             id: 'chrome-extension://fake',
         },
         loadTimes: () => ({
             requestTime: 0, startLoadTime: 0, commitLoadTime: 0,
             finishDocumentLoadTime: 0, finishLoadTime: 0,
             firstPaintTime: 0, firstPaintAfterLoadTime: 0,
             navigationType: 'other', wasFetchedViaSpdy: false,
             wasNpnNegotiated: false, npnNegotiatedProtocol: 'http/1.1',
             wasAlternateProtocolAvailable: false, connectionInfo: 'http/1.1',
         }),
         csi: () => ({ startE: 0, onloadT: 0, pageT: 0 }),
         app: {
             isInstalled: false,
             InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
             RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
         },
         webstore: { onInstallStageChanged: {}, onDownloadProgress: {} },
         runtime: {},
     };

     Object.defineProperty(navigator, 'plugins', {
         get: () => {
             const plugins = [
                 { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                 { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                 { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
             ];
             plugins.item = (i) => plugins[i];
             plugins.namedItem = (n) => plugins.find(p => p.name === n) || null;
             plugins.refresh = () => {};
             plugins.length = plugins.length;
             return plugins;
         },
         configurable: true,
     });

     Object.defineProperty(navigator, 'languages', {
         get: () => ['es-ES', 'es', 'en-US', 'en'],
         configurable: true,
     });

     Object.defineProperty(navigator, 'hardwareConcurrency', {
         get: () => 8, configurable: true,
     });

     Object.defineProperty(navigator, 'deviceMemory', {
         get: () => 8, configurable: true,
     });

     Object.defineProperty(navigator, 'maxTouchPoints', {
         get: () => 0, configurable: true,
     });

     Object.defineProperty(navigator, 'vendor', {
         get: () => 'Google Inc.', configurable: true,
     });

     Object.defineProperty(navigator, 'platform', {
         get: () => 'Win32', configurable: true,
     });

     if (window.navigator.permissions) {
         const origQuery = window.navigator.permissions.query;
         window.navigator.permissions.query = (params) => (
             params.name === 'notifications'
                 ? Promise.resolve({ state: 'denied', onchange: null })
                 : origQuery(params)
         );
     }

     const deleteKeys = [
         'cdc_adoQpoasnfa76pfcZLmcfl_', '__pw_manual', '__playwright',
         'playwright', '__puppeteer', 'puppeteer', '__selenium_evaluate',
         'selenium', '__webdriver_evaluate', '__fxdriver_evaluate',
         '__driver_evaluate', '__webdriver_script_function',
         '__webdriver_unwrapped', '__driver_unwrapped', '__selenium_unwrapped',
         '__fxdriver_unwrapped', '_phantom', 'phantom', 'callPhantom',
         'domAutomation', 'domAutomationController',
     ];
     deleteKeys.forEach(key => {
         try { if (key in window) delete window[key]; } catch(e) {}
     });

     const globalVarCheck = '$cdc_asdjflasutopfhvcZLmcfl_';
     try {
         if (globalVarCheck in window) delete window[globalVarCheck];
         Object.defineProperty(window, globalVarCheck, {
             get: () => undefined, set: () => {}, configurable: false,
         });
     } catch(e) {}

     Object.defineProperty(document, '__webdriver_script_fn', {
         get: () => undefined, configurable: true,
     });

     const origToString = Function.prototype.toString;
     Function.prototype.toString = function() {
         const str = origToString.call(this);
         if (str.includes('native code')) return str;
         if (this === Function.prototype.toString) return 'function toString() { [native code] }';
         return str;
     };
"""

    def get_token(self, user_agent: str = None):
        """
        Generate a fresh blackbox token.

        A threading lock serializes Playwright calls to prevent uvloop race
        conditions when multiple requests arrive concurrently. When no
        user_agent is provided, a random one from the supported list is used.

        Args:
        - user_agent (str, optional): The user agent string to use for the browser.

        Returns:
        - str: The generated token.
        """
        effective_ua = user_agent if user_agent else random.choice(self.supported_user_agents)

        with self._lock:
            return self._generate_token(effective_ua)

    def _generate_token(self, user_agent: str):
        """
        Launch Playwright to generate a fresh token.

        Args:
        - user_agent (str): The user agent string to use for the browser.

        Returns:
        - str: The generated token.
        """
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=settings.PLAYWRIGHT_HEADLESS,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            context = browser.new_context(user_agent=user_agent)
            context.add_init_script(self._stealth_script)
            page = context.new_page()
            page.goto(self.html_file_path)
            token_element = page.wait_for_selector("body > div")
            token = token_element.inner_text()
            browser.close()
        return token
