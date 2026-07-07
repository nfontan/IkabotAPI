import logging
import os
import random
import threading

from playwright.sync_api import sync_playwright

import settings

logger = logging.getLogger(__name__)


class TokenGenerator:

    def __init__(self, supported_user_agents):
        port = os.getenv("PORT", "5005")
        self.token_page_url = f"http://localhost:{port}/v1/token-page"
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
         loadTimes: () => ({ requestTime: 0, startLoadTime: 0, commitLoadTime: 0, finishDocumentLoadTime: 0, finishLoadTime: 0, firstPaintTime: 0, firstPaintAfterLoadTime: 0, navigationType: 'other', wasFetchedViaSpdy: false, wasNpnNegotiated: false, npnNegotiatedProtocol: 'http/1.1', wasAlternateProtocolAvailable: false, connectionInfo: 'http/1.1' }),
         csi: () => ({ startE: 0, onloadT: 0, pageT: 0 }),
         app: { isInstalled: false, InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }, RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' } },
         webstore: { onInstallStageChanged: {}, onDownloadProgress: {} },
         runtime: {},
     };

     Object.defineProperty(navigator, 'plugins', {
         get: () => { const p = [ { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }, { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' }, { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' } ]; p.item = (i) => p[i]; p.namedItem = (n) => p.find(x => x.name === n) || null; p.refresh = () => {}; return p; },
         configurable: true,
     });

     Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en-US', 'en'], configurable: true });
     Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8, configurable: true });
     Object.defineProperty(navigator, 'deviceMemory', { get: () => 8, configurable: true });
     Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0, configurable: true });
     Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.', configurable: true });
     Object.defineProperty(navigator, 'platform', { get: () => 'Win32', configurable: true });

     if (window.navigator.permissions) {
         const q = window.navigator.permissions.query;
         window.navigator.permissions.query = (p) => p.name === 'notifications' ? Promise.resolve({ state: 'denied', onchange: null }) : q(p);
     }

     ['cdc_adoQpoasnfa76pfcZLmcfl_', '__pw_manual', '__playwright', 'playwright', '__puppeteer', 'puppeteer', '__selenium_evaluate', 'selenium', '__webdriver_evaluate', '__fxdriver_evaluate', '__driver_evaluate', '__webdriver_script_function', '__webdriver_unwrapped', '__driver_unwrapped', '__selenium_unwrapped', '__fxdriver_unwrapped', '_phantom', 'phantom', 'callPhantom', 'domAutomation', 'domAutomationController', '__puppeteer_evaluation_script__'].forEach(k => { try { if (k in window) delete window[k]; } catch(e) {} });

     try { if ('$cdc_asdjflasutopfhvcZLmcfl_' in window) delete window['$cdc_asdjflasutopfhvcZLmcfl_']; Object.defineProperty(window, '$cdc_asdjflasutopfhvcZLmcfl_', { get: () => undefined, set: () => {}, configurable: false }); } catch(e) {}

     Object.defineProperty(document, '__webdriver_script_fn', { get: () => undefined, configurable: true });

     const _t = Function.prototype.toString;
     Function.prototype.toString = function() { const s = _t.call(this); if (s.includes('native code') || this === Function.prototype.toString) return 'function toString() { [native code] }'; return s; };
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
            logger.info(f"Loading token page from: {self.token_page_url}")
            page.goto(self.token_page_url)
            logger.info("Token page loaded, waiting for token element")
            token_element = page.wait_for_selector("body > div")
            token = token_element.inner_text()
            logger.info(f"Token obtained, length={len(token)}")
            browser.close()
        return token
