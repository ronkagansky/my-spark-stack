from playwright.async_api import async_playwright, Browser, Page
from typing import List, Optional
import asyncio
import gc
from dataclasses import dataclass


@dataclass
class PageCheckResult:
    """Result of checking a page for errors and console messages."""

    errors: List[str]
    console: List[str]


class BrowserMonitor:
    _instance = None
    _initialized = False
    _last_gc_time = 0
    _GC_INTERVAL = 300  # Run garbage collection every 5 minutes

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not BrowserMonitor._initialized:
            self._browser: Optional[Browser] = None
            self._page: Optional[Page] = None
            self._console_messages: List[str] = []
            self._page_errors: List[str] = []
            self._lock = asyncio.Lock()
            self._playwright = None
            BrowserMonitor._initialized = True

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = BrowserMonitor()
        return cls._instance

    async def _ensure_setup(self):
        if not self._browser:
            await self._setup()

    async def _setup(self):
        """Initialize the browser and page with memory-optimized settings."""
        if self._browser is not None:
            await self.cleanup()

        self._playwright = await async_playwright().start()

        # Launch browser with memory-saving arguments
        self._browser = await self._playwright.chromium.launch(
            args=[
                "--single-process",  # Use single process
                "--disable-gpu",  # Disable GPU hardware acceleration
                "--disable-dev-shm-usage",  # Overcome limited /dev/shm in containers
                "--no-sandbox",  # Required for running in containers
                "--disable-setuid-sandbox",
                "--disable-accelerated-2d-canvas",
                "--disable-speech-api",  # Disable unnecessary APIs
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-extensions",
                "--disable-component-extensions-with-background-pages",
                "--disable-ipc-flooding-protection",
                '--js-flags="--expose-gc"',  # Enable manual garbage collection
            ]
        )

        # Create a single reusable page
        self._page = await self._browser.new_page()

        # Configure page for memory optimization
        await self._page.route(
            "**/*", lambda route: route.continue_()
        )  # Minimal routing
        await self._page.set_viewport_size({"width": 1280, "height": 720})

        # Listen for console messages
        self._page.on(
            "console",
            lambda msg: self._console_messages.append(f"[{msg.type}] {msg.text}"),
        )
        # Listen for page errors
        self._page.on(
            "pageerror", lambda err: self._page_errors.append(f"Page error: {err}")
        )

    async def _maybe_run_gc(self):
        """Run garbage collection if enough time has passed."""
        current_time = asyncio.get_event_loop().time()
        if current_time - self._last_gc_time > self._GC_INTERVAL:
            if self._page:
                try:
                    await self._page.evaluate("() => { if (window.gc) window.gc() }")
                except Exception:
                    pass  # Ignore if gc is not available
            gc.collect()  # Python-level garbage collection
            self._last_gc_time = current_time

    def _clear_state(self):
        self._console_messages = []
        self._page_errors = []

    async def check_page(
        self, url: str, wait_time: int = 2, lock_timeout: float = 5.0
    ) -> Optional[PageCheckResult]:
        """Navigate to the URL and check for errors/messages.

        Args:
            url: The URL to check
            wait_time: Time to wait after page load to capture errors
            lock_timeout: Maximum time to wait for lock acquisition in seconds
        """
        try:
            # Try to acquire the lock with timeout
            try:
                await asyncio.wait_for(self._lock.acquire(), timeout=lock_timeout)
            except asyncio.TimeoutError:
                return PageCheckResult(
                    errors=[],
                    console=[
                        f"Browser status not currently available. This is not an error."
                    ],
                )

            await self._ensure_setup()

            try:
                # Clear memory before loading new page
                await self._maybe_run_gc()

                await self._page.goto(url, wait_until="networkidle")
                # Clear previous errors/messages
                self._clear_state()

                # Wait for specified time to capture any errors
                await asyncio.sleep(wait_time)

                return PageCheckResult(
                    errors=self._page_errors.copy(),
                    console=self._console_messages.copy(),
                )
            except Exception as e:
                print(f"Error checking page: {e}")
                return PageCheckResult(errors=[f"Error checking page: {e}"], console=[])
            finally:
                self._lock.release()
        except asyncio.TimeoutError:
            return PageCheckResult(
                errors=[],
                console=[],
            )

    async def cleanup(self):
        """Clean up browser resources."""
        if self._page:
            await self._maybe_run_gc()
            await self._page.close()
            self._page = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        self._clear_state()
        gc.collect()  # Final garbage collection
