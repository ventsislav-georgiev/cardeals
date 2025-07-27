"""
Base scraper class with common functionality
"""

import requests
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from models.car import Car
from utils.logger import setup_logger


class BaseScraper(ABC):
    """Base class for all car listing scrapers"""
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.session = requests.Session()
        
        # Use a hardcoded user agent to avoid fake_useragent delays
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # More sophisticated headers to avoid bot detection
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,bg;q=0.8,de;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        })
    
    def get_page(self, url: str, params: Optional[Dict[str, Any]] = None, retry_count: int = 3) -> BeautifulSoup:
        """
        Fetch a page and return BeautifulSoup object
        
        Args:
            url: URL to fetch
            params: Query parameters
            retry_count: Number of retries for failed requests
            
        Returns:
            BeautifulSoup object of the page content
        """
        for attempt in range(retry_count):
            try:
                self.logger.debug(f"Fetching: {url} (attempt {attempt + 1})")
                
                # Keep the same user agent for consistency
                # self.session.headers['User-Agent'] already set in __init__
                
                # Add some randomness to delays
                if attempt > 0:
                    delay = 2 + attempt * 2  # Increasing delay for retries
                    self.logger.debug(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                # Add random delay to be more human-like
                import random
                delay = random.uniform(1, 3)
                time.sleep(delay)
                
                # Save the HTML for debugging
                with open("debug_mobilebg.html", "wb") as f:
                    f.write(response.content)
                return BeautifulSoup(response.content, 'lxml')
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    self.logger.warning(f"403 Forbidden error on attempt {attempt + 1}")
                    if attempt < retry_count - 1:
                        continue
                self.logger.error(f"HTTP Error fetching {url}: {str(e)}")
                raise
            except requests.RequestException as e:
                self.logger.error(f"Error fetching {url}: {str(e)}")
                if attempt < retry_count - 1:
                    continue
                raise
    
    @abstractmethod
    def build_search_url(self, params: Dict[str, Any]) -> str:
        """Build search URL from parameters"""
        pass
    
    @abstractmethod
    def parse_listing_page(self, soup: BeautifulSoup, page_num: int = 1) -> List[Car]:
        """Parse a listing page and extract car information"""
        pass
    
    @abstractmethod
    def get_total_pages(self, soup: BeautifulSoup) -> int:
        """Get total number of pages from the first page"""
        pass
    
    def scrape(self, search_params: Dict[str, Any], max_pages: int = 50) -> List[Car]:
        """
        Main scraping method
        
        Args:
            search_params: Search parameters
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of Car objects
        """
        all_cars = []
        
        try:
            # Build initial search URL
            base_url = self.build_search_url(search_params)
            
            # Get first page to determine total pages
            soup = self.get_page(base_url)
            total_pages = min(self.get_total_pages(soup), max_pages)
            
            self.logger.info(f"Found {total_pages} pages to scrape")
            
            # Parse first page
            self.logger.info(f"Scraping page 1: {base_url}")
            cars = self.parse_listing_page(soup, 1)
            all_cars.extend(cars)
            self.logger.debug(f"Page 1: Found {len(cars)} cars")

            # Parse remaining pages
            for page_num in range(2, total_pages + 1):
                try:
                    page_url = self.build_page_url(base_url, page_num)
                    self.logger.info(f"Scraping page {page_num}: {page_url}")
                    soup = self.get_page(page_url)
                    cars = self.parse_listing_page(soup, page_num)
                    all_cars.extend(cars)
                    self.logger.debug(f"Page {page_num}: Found {len(cars)} cars")

                except Exception as e:
                    self.logger.warning(f"Error parsing page {page_num}: {str(e)}")
                    continue
            
            self.logger.info(f"Completed scraping. Total cars found: {len(all_cars)}")
            return all_cars
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
            return all_cars
    
    
    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean and normalize text"""
        if not text:
            return None
        return text.strip().replace('\n', ' ').replace('\t', ' ')
    
    def extract_number(self, text: Optional[str]) -> Optional[int]:
        """Extract number from text"""
        if not text:
            return None
        
        import re
        numbers = re.findall(r'\d+', text.replace(',', '').replace(' ', ''))
        return int(''.join(numbers)) if numbers else None
