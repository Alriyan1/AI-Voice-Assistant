from playwright.async_api import async_playwright,Browser,BrowserContext,Page
from typing import Optional,List,Dict
from pathlib import Path
from loguru import logger
from pydantic import BaseModel
import asyncio
from config.settings import settings

class BrowserResult(BaseModel):
    success: bool
    message: str
    url: Optional[str]=None
    content: Optional[str]=None
    screenshot: Optional[bytes]=None


class BrowserTools:
    def __init__(self):
        self.browser: Optional[Browser]=None
        self.context: Optional[BrowserContext]=None
        self.page: Optional[Page]=None
        self._playwright=None
        self.headless=settings.browser_headless
        self.timeout=settings.browser_timeout


    async def initialize(self)->bool:

        try:
            self._playwright = await async_playwright().start()

            launch_kwargs = {
                'headless': self.headless,
                'args': ['--disable-blink-features=AutomationControlled'],
            }

            chrome_path = str(settings.chrome_path).strip()
            if chrome_path and Path(chrome_path).exists():
                launch_kwargs['executable_path'] = chrome_path
            elif __import__('os').name == 'nt':
                launch_kwargs['channel'] = 'chrome'

            self.browser = await self._playwright.chromium.launch(**launch_kwargs)

            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/127.0.0.0 Safari/537.36'
                )
            )

            self.page = await self.context.new_page()
            logger.info('Browser initialized')
            return True

        except Exception as e:
            logger.error(f"Browser initialization failed: {e}")
            return False


    async def close(self)->None:
        try:
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info('Browser closed')
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def navigate_to(self,url:str)->BrowserResult:

        try:
            if not self.page:
                await self.initialize()
            await self.page.goto(url,timeout=self.timeout,wait_until='domcontentloaded')
            title = await self.page.title()

            logger.info(f"Navigated to: {url} ({title})")

            return BrowserResult(
                success=True,
                message=f"Opened: {title}",
                url=url
            )        

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return BrowserResult(
                success=False,
                message=f"Failed to open: {str(e)}",
                url=url
            )

    async def search_google(self,query:str)->BrowserResult:
        try:
            if not self.page:
                await self.initialize()

            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

            await self.page.goto(search_url,timeout=self.timeout,wait_until='domcontentloaded')

            title = await self.page.title()
            logger.info(f"Google search: {query}")

            return BrowserResult(
                success=True,
                message=f"Searched Google for: {query}",
                url=search_url
            )

        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return BrowserResult(
                success=False,
                message=f"Search failed: {str(e)}"
            )

    async def search_youtube(self,query:str) -> BrowserResult:
        try:
            if not self.page:
                await self.initialize()

            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"

            await self.page.goto(search_url,timeout=self.timeout,wait_until='domcontentloaded')

            logger.info(f"YouTube search: {query}")

            return BrowserResult(
                success=True,
                message=f"Searched YouTube for: {query}",
                url=search_url
            )

        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return BrowserResult(
                success=False,
                message=f"Search failed: {str(e)}"
            )

    async def click_element(self,selector:str) -> BrowserResult:
        try:
            if not self.page:
                return BrowserResult(
                    success=False,
                    message="Browser not initiazlized"
                )

            await self.page.click(selector,timeout=self.timeout)
            await self.page.wait_for_load_state('domcontentloaded')

            logger.info(f"Clicked: {selector}")

            return BrowserResult(
                success=True,
                message=f"Clicked element: {selector}"
            )
            
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return BrowserResult(
                success=False,
                message=f"Click failed: {str(e)}"
            )

    async def fill_form(self,selector:str,value:str)->BrowserResult:

        try:
            if not self.page:
                return BrowserResult(
                    success=False,
                    message="Browser not initialized"
                )
            
            await self.page.fill(selector, value, timeout=self.timeout)
            logger.info(f"Filled {selector} with: {value}")
            
            return BrowserResult(
                success=True,
                message=f"Filled field: {selector}"
            )
            
        except Exception as e:
            logger.error(f"Fill failed: {e}")
            return BrowserResult(
                success=False,
                message=f"Fill failed: {str(e)}"
            )

    async def get_page_content(self)->BrowserResult:

        try:
            if not self.page:
                return BrowserResult(
                    success=False,
                    message="Browser not initialized"
                )

            content = await self.page.content()
            title = await self.page.title()
            url = self.page.url

            logger.info(f"Got content from: {url}")
            
            return BrowserResult(
                success=True,
                message=f"Retrieved content from: {title}",
                url=url,
                content=content
            )
            
        except Exception as e:
            logger.error(f"Get content failed: {e}")
            return BrowserResult(
                success=False,
                message=f"Failed to get content: {str(e)}"
            )


    async def take_screenshot(self)->BrowserResult:
        try:
            if not self.page:
                return BrowserResult(
                    success=False,
                    message="Browser not initialized"
                )

            screenshot = await self.page.screenshot(full_page=True)
            url = self.page.url

            logger.info(f"Screenshot taken: {url}")

            return BrowserResult(
                success=True,
                message='Screenshot captured',
                url=url,
                screenshot=screenshot
            )

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return BrowserResult(
                success=False,
                message=f"Screenshot failed: {str(e)}"
            )

    async def download_file(self,url:str,save_path:str)->BrowserResult:

        try:
            if not self.page:
                await self.initialize()

            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {value: undefined});
            """)

            await self.page.goto(url,timeout=self.timeout)
            logger.info(f"Downloaded: {url}")

            return BrowserResult(
                success=True,
                message=f"Downloaded: {url}",
                url=url
            )
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return BrowserResult(
                success=False,
                message=f"Download failed:{str(e)}"
            )