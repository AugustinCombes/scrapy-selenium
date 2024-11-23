"""This module contains the ``SeleniumMiddleware`` scrapy middleware"""

from importlib import import_module
import subprocess
import logging
from packaging import version

from scrapy import signals
from scrapy.exceptions import NotConfigured
from scrapy.http import HtmlResponse
from selenium.webdriver.support.ui import WebDriverWait

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from .http import SeleniumRequest

logger = logging.getLogger(__name__)

class SeleniumMiddleware:
    """Scrapy middleware handling the requests using selenium"""

    def get_chrome_version(self):
        """Get the version of installed Chrome browser"""
        try:
            # For MacOS
            cmd = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()
            chrome_version = output.decode("utf-8").strip().split()[-1]
            logger.info(f"Detected Chrome version: {chrome_version}")
            return chrome_version
        except Exception as e:
            logger.warning(f"Could not determine Chrome version: {e}")
            return None

    def get_matching_chromedriver(self, chrome_version):
        """Get the appropriate ChromeDriver version"""
        try:
            if chrome_version:
                major_version = version.parse(chrome_version).major
                logger.info(f"Looking for ChromeDriver version matching Chrome {major_version}")
                return ChromeDriverManager(version=f"{major_version}").install()
            else:
                logger.info("Using latest ChromeDriver version")
                return ChromeDriverManager().install()
        except Exception as e:
            logger.warning(f"Error getting matching ChromeDriver: {e}. Falling back to latest version.")
            return ChromeDriverManager().install()

    def __init__(self, driver_arguments=None):
        """Initialize the selenium webdriver

        Parameters
        ----------
        driver_arguments: list
            A list of arguments to initialize the driver
        """
        chrome_options = Options()
        if driver_arguments:
            for argument in driver_arguments:
                chrome_options.add_argument(argument)
                
        chrome_version = self.get_chrome_version()
        driver_path = self.get_matching_chromedriver(chrome_version)
        
        service = Service(driver_path)
        logger.info(f"Initializing Chrome WebDriver with service path: {driver_path}")
        
        try:
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise

    @classmethod
    def from_crawler(cls, crawler):
        """Initialize the middleware with the crawler settings"""
        driver_arguments = crawler.settings.get('SELENIUM_DRIVER_ARGUMENTS')

        if not driver_arguments:
            logger.warning('SELENIUM_DRIVER_ARGUMENTS not set, proceeding with default options')
            
        middleware = cls(driver_arguments=driver_arguments)
        crawler.signals.connect(middleware.spider_closed, signals.spider_closed)
        return middleware

    def process_request(self, request, spider):
        """Process a request using the selenium driver if applicable"""
        if not isinstance(request, SeleniumRequest):
            return None

        self.driver.get(request.url)

        for cookie_name, cookie_value in request.cookies.items():
            self.driver.add_cookie(
                {
                    'name': cookie_name,
                    'value': cookie_value
                }
            )

        if request.wait_until:
            WebDriverWait(self.driver, request.wait_time).until(
                request.wait_until
            )

        if request.screenshot:
            request.meta['screenshot'] = self.driver.get_screenshot_as_png()

        if request.script:
            self.driver.execute_script(request.script)

        body = str.encode(self.driver.page_source)
        request.meta.update({'driver': self.driver})

        return HtmlResponse(
            self.driver.current_url,
            body=body,
            encoding='utf-8',
            request=request
        )

    def spider_closed(self):
        """Shutdown the driver when spider is closed"""
        self.driver.quit()