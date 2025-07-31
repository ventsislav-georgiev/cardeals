"""
Mobile.bg scraper implementation
"""

import re
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urljoin, urlencode
from bs4 import BeautifulSoup, Tag, NavigableString
from models.car import Car
from scrapers.base import BaseScraper


class MobileBgScraper(BaseScraper):
    def __init__(self, verbose: bool = False):
        super().__init__()
        self.verbose = verbose
    """Scraper for mobile.bg car listings"""

    BASE_URL = "https://mobile.bg"
    
    # EUR to BGN exchange rate (approximate)
    EUR_TO_BGN_RATE = 2.0
    
    def build_page_url(self, base_url: str, page_num: int) -> str:
        """Build URL for a specific page number for mobile.bg (use /p-{page_num} before query string)"""
        if page_num == 1:
            return base_url
        if '?' in base_url:
            path, query = base_url.split('?', 1)
            return f"{path}/p-{page_num}?{query}"
        else:
            return f"{base_url}/p-{page_num}"

    def build_search_url(self, params: Dict[str, Any]) -> str:
        """
        Build search URL for mobile.bg using the path-based structure
        Based on: https://www.mobile.bg/obiavi/avtomobili-dzhipove/mercedes-benz/glc-klasa/dizelov/avtomatichna/ot-2019/namira-se-v-balgariya?price1=70000
        """
        
        # Build the path-based URL structure
        path_parts = ["obiavi", "avtomobili-dzhipove"]
        
        # Add brand (convert to lowercase with dashes, handle special cases)
        brand = params.get('brand')
        if brand:
            brand_slug = brand.lower().replace(' ', '-')
            # Handle special brand mappings for mobile.bg
            brand_mapping = {
                'mercedes': 'mercedes-benz',
                'vw': 'volkswagen',
                'bmw': 'bmw',
                'audi': 'audi'
            }
            brand_slug = brand_mapping.get(brand_slug, brand_slug)
            if brand_slug:  # Only append if not None
                path_parts.append(brand_slug)
        
        # Add model (convert to lowercase with dashes, handle special cases)
        model = params.get('model')
        if model:
            model_slug = model.lower().replace(' ', '-')
            # Handle special model mappings for mobile.bg
            model_mapping = {
                'glc': 'glc-klasa',
                'glc-class': 'glc-klasa',
                'c-class': 'c-klasa',
                'e-class': 'e-klasa',
                's-class': 's-klasa',
                'a-class': 'a-klasa',
                'b-class': 'b-klasa'
            }
            model_slug = model_mapping.get(model_slug, model_slug)
            if model_slug:  # Only append if not None
                path_parts.append(model_slug)
        
        # Add engine type
        engine_type = params.get('engine_type')
        if engine_type:
            engine_map = {
                'diesel': 'dizelov',
                'petrol': 'benzinovs',
                'electric': 'elektricheski',
                'hybrid': 'hibridni'
            }
            if engine_type in engine_map:
                path_parts.append(engine_map[engine_type])
        
        # Add gearbox type
        gearbox_type = params.get('gearbox_type')
        if gearbox_type:
            gearbox_map = {
                'automatic': 'avtomatichna',
                'manual': 'rychna'
            }
            if gearbox_type in gearbox_map:
                path_parts.append(gearbox_map[gearbox_type])
        
        # Add year
        year_start = params.get('year_start')
        if year_start:
            path_parts.append(f'ot-{year_start}')
        
        # Add location filter (Bulgaria)
        path_parts.append('namira-se-v-balgariya')
        
        # Build URL
        url = f"{self.BASE_URL}/{'/'.join(path_parts)}"
        
        # Add query parameters
        query_params = {}
        price_max = params.get('price_max')
        if price_max:
            # Convert EUR to BGN (approximately 1 EUR = 2 BGN)
            bgn_price = int(price_max * self.EUR_TO_BGN_RATE)
            query_params['price1'] = str(bgn_price)
        
        # query_params['extri'] = '17'  # Always include extra parameter for air suspension
        
        if query_params:
            url += "?" + urlencode(query_params)
        
        if self.verbose:
            self.logger.debug(f"Built mobile.bg search URL: {url}")
        return url
    
    def get_total_pages(self, soup: BeautifulSoup) -> int:
        """Extract total number of pages from search results"""
        try:
            # Look for pagination - mobile.bg uses simple pagination
            # Check for "Напред" (Next) link or page numbers
            pagination_links = soup.find_all('a', href=True)
            
            page_numbers = []
            has_next = False
            
            for link in pagination_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Check for "Next" link
                if 'напред' in text.lower() or 'next' in text.lower() or '›' in text:
                    has_next = True
                
                # Extract page numbers from URLs or text
                if 'page=' in href or text.isdigit():
                    if text.isdigit():
                        page_numbers.append(int(text))
                    else:
                        # Extract page number from URL
                        page_match = re.search(r'page=(\d+)', href)
                        if page_match:
                            page_numbers.append(int(page_match.group(1)))
            
            if page_numbers:
                return max(page_numbers)
            elif has_next:
                return 2  # At least 2 pages if there's a "next" link
            else:
                return 1
                
        except Exception as e:
            self.logger.warning(f"Could not determine total pages: {str(e)}")
            return 1
    
    def parse_listing_page(self, soup: BeautifulSoup, page_num: int = 1) -> List[Car]:
        """Parse a listing page and extract car information, then crawl each car's detail page for created date"""
        import requests
        cars = []
        try:
            selectors = [
                'div.item',  # Primary mobile.bg selector (current structure)
                'div.l',
                'div.o',
                'div#content div.l',
                'div#content div.o',
                'div[class*="searchResultsItem"]',
                'div[class*="result-item"]',
                'div[class*="listItem"]',
            ]
            items = []
            for sel in selectors:
                found = soup.select(sel)
                if found:
                    items.extend(found)
            items = list(dict.fromkeys(items))
            if not items:
                all_divs = soup.find_all('div')
                items = [div for div in all_divs if self._looks_like_car_listing(div)]
            if self.verbose:
                self.logger.info(f"[mobile.bg] Found {len(items)} car listing divs on page {page_num}")
                for i, item in enumerate(items[:3]):
                    title = item.get_text(strip=True)[:120]
                    self.logger.info(f"[mobile.bg] Example listing {i+1}: {title}")
            filtered_items = [item for item in items if not (
                'resultsInfoBox' in item.get('class', []) or
                'paramsFromSearchText' in item.get('class', []) or
                item.get('id', '') == 'paramsFromSearchText'
            )]
            if self.verbose and filtered_items:
                try:
                    with open("debug_first_listing.html", "w", encoding="utf-8") as f:
                        for i, div in enumerate(filtered_items[:5]):
                            f.write(f"\n<!-- Listing Candidate {i+1} -->\n")
                            f.write(str(div))
                            f.write("\n\n")
                    self.logger.info("[mobile.bg] Saved first 5 real car listing candidates to debug_first_listing.html")
                except Exception as e:
                    self.logger.warning(f"[mobile.bg] Could not save debug_first_listing.html: {e}")
            items = filtered_items
            if self.verbose and not items:
                all_divs = soup.find_all('div')
                print("\n[DEBUG] First 10 <div> elements on the page (full HTML):", flush=True)
                for i, div in enumerate(all_divs[:10]):
                    print(f"[DEBUG] DIV {i+1} HTML:\n{div.prettify()[:800]}\n{'-'*60}", flush=True)
            for item in items:
                try:
                    car = self.parse_car_item(item)
                    if car and car.listing_url:
                        # Crawl detail page for created date
                        try:
                            detail_resp = requests.get(car.listing_url, timeout=10)
                            if detail_resp.status_code == 200:
                                detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                                created_date = self.extract_created_date(detail_soup)
                                car.created_date = created_date if created_date else None
                        except Exception as e:
                            self.logger.warning(f"Could not fetch detail page for {car.listing_url}: {e}")
                        cars.append(car)
                except Exception as e:
                    self.logger.warning(f"Error parsing car item: {str(e)}")
                    continue
        except Exception as e:
            self.logger.error(f"Error parsing listing page {page_num}: {str(e)}")
        unique = {}
        for car in cars:
            if car.listing_url and car.listing_url not in unique:
                unique[car.listing_url] = car
        deduped_cars = list(unique.values())
        if self.verbose:
            self.logger.info(f"[mobile.bg] Successfully parsed {len(deduped_cars)} unique cars from page {page_num}")
        return deduped_cars

    def extract_created_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract created date from price history via AJAX or fallback patterns"""
        import requests
        import json
        from urllib.parse import quote
        from datetime import datetime
        
        # First try to get price history via AJAX
        try:
            # Extract listing ID from page URL or content
            listing_id = None
            
            # Look for listing ID in the page
            id_patterns = [
                r'obiava-(\d+)-',  # from URL
                r'ida[\'"]?\s*:\s*[\'"]?(\d+)',  # from JavaScript
                r'listing.*?(\d{20})',  # long number pattern
            ]
            
            page_content = str(soup)
            for pattern in id_patterns:
                match = re.search(pattern, page_content)
                if match:
                    listing_id = match.group(1)
                    break
            
            if listing_id:
                # Try to extract current price for AJAX call
                current_price = "0"
                price_elements = soup.find_all(text=re.compile(r'\d+\s*лв'))
                if price_elements:
                    price_text = str(price_elements[0])
                    price_match = re.search(r'(\d+)', price_text)
                    if price_match:
                        current_price = price_match.group(1)
                
                # Make AJAX request to get price history
                ajax_session = requests.Session()
                ajax_session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded'
                })
                
                params = {
                    'act': '3',
                    'ida': listing_id,
                    'pr': quote(current_price),
                    'cr': quote('лв.'),
                    'mode': '1'
                }
                
                response = ajax_session.post("https://www.mobile.bg/pcgi/subscript.cgi", 
                                           data=params, timeout=10)
                
                if response.status_code == 200:
                    json_data = json.loads(response.text)
                    if json_data.get('result') == 1 and 'table' in json_data:
                        table_html = json_data['table']
                        
                        # Parse the price history table
                        table_soup = BeautifulSoup(table_html, 'html.parser')
                        divs = table_soup.find_all('div')
                        
                        dates_with_times = []
                        
                        for div in divs:
                            text = div.get_text(strip=True)
                            # Look for date-time patterns: "DD.MM в HH.MM ч."
                            date_time_match = re.match(r'(\d{2})\.(\d{2})\s+в\s+(\d{2})\.(\d{2})\s+ч\.', text)
                            if date_time_match:
                                day = int(date_time_match.group(1))
                                month = int(date_time_match.group(2))
                                hour = int(date_time_match.group(3))
                                minute = int(date_time_match.group(4))
                                dates_with_times.append((month, day, hour, minute, text))
                        
                        if dates_with_times:
                            # Sort by month, day, then time to find the earliest
                            earliest = min(dates_with_times, key=lambda x: (x[0], x[1], x[2], x[3]))
                            
                            # Find fallback year from other parts of the page
                            fallback_year = None
                            fallback_patterns = [
                                r'Редактирана в [^н]+ на [^г]+(\d{4}) год\.',
                                r'Публикувана в [^н]+ на [^г]+(\d{4}) год\.',
                                r'(\d{4}) год\.',
                            ]
                            
                            for div in soup.find_all('div'):
                                if not isinstance(div, Tag):
                                    continue
                                div_text = div.get_text()
                                for pat in fallback_patterns:
                                    match = re.search(pat, div_text)
                                    if match:
                                        fallback_year = match.group(1)
                                        break
                                if fallback_year:
                                    break
                            
                            if not fallback_year:
                                # Default to current year if no fallback found
                                fallback_year = str(datetime.now().year)
                            
                            month, day, hour, minute = earliest[:4]
                            
                            return f"{fallback_year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:00"
        
        except Exception as e:
            pass  # Fall back to static extraction
        
        # Fallback to original extraction logic
        return self._extract_created_date_fallback(soup)

    def _extract_created_date_fallback(self, soup: BeautifulSoup) -> Optional[str]:
        """Fallback method for extracting created date from static HTML"""
        # First try to find price history
        price_history_div = soup.find('div', id='priceHistory')
        statistiki_tag = None
        
        if price_history_div and isinstance(price_history_div, Tag):
            for child in price_history_div.children:
                if isinstance(child, Tag) and child.name == 'statistiki':
                    statistiki_tag = child
                    break
        
        if statistiki_tag and isinstance(statistiki_tag, Tag):
            divs = [d for d in statistiki_tag.find_all('div') if isinstance(d, Tag)]
            dates_with_times = []
            
            for div in divs:
                text = div.get_text(strip=True)
                # Look for date-time patterns: "DD.MM в HH.MM ч."
                date_time_match = re.match(r'(\d{2})\.(\d{2})\s+в\s+(\d{2})\.(\d{2})\s+ч\.', text)
                if date_time_match:
                    day = int(date_time_match.group(1))
                    month = int(date_time_match.group(2))
                    hour = int(date_time_match.group(3))
                    minute = int(date_time_match.group(4))
                    dates_with_times.append((month, day, hour, minute, text))
            
            if dates_with_times:
                # Sort to find the earliest date/time
                earliest = min(dates_with_times, key=lambda x: (x[0], x[1], x[2], x[3]))
                
                # Look for fallback year and time in the page
                fallback_year = None
                fallback_patterns = [
                    r'Редактирана в [^н]+ на [^г]+(\d{4}) год\.',
                    r'Публикувана в [^н]+ на [^г]+(\d{4}) год\.',
                    r'(\d{4}) год\.',
                ]
                
                for div in soup.find_all('div'):
                    if not isinstance(div, Tag):
                        continue
                    div_text = div.get_text()
                    for pat in fallback_patterns:
                        match = re.search(pat, div_text)
                        if match:
                            fallback_year = match.group(1)
                            break
                    if fallback_year:
                        break
                
                if not fallback_year:
                    from datetime import datetime
                    fallback_year = str(datetime.now().year)
                
                month, day, hour, minute = earliest[:4]
                return f"{fallback_year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:00"
        
        # Final fallback to basic pattern matching
        import re
        statistiki = None
        for div in soup.find_all('div'):
            if div.get('class') and 'statistiki' in div.get('class'):
                statistiki = div
                break
        if statistiki:
            text_div = None
            for child in statistiki.find_all('div'):
                if child.get('class') and 'text' in child.get('class'):
                    text_div = child
                    break
            if text_div:
                txt = text_div.get_text()
                patterns = [
                    r'Публикувана в ([0-9]{2}:[0-9]{2}) часа на ([0-9]{2}\.[0-9]{2}\.[0-9]{4}) год\.',  # Prioritize original publication date
                    r'Редактирана в ([0-9]{2}:[0-9]{2}) часа на ([0-9]{2}\.[0-9]{2}\.[0-9]{4}) год\.',  # Fallback to edited date
                    r'([0-9]{2}:[0-9]{2}) часа на ([0-9]{2}\.[0-9]{2}\.[0-9]{4})',
                    r'([0-9]{2}\.[0-9]{2}\.[0-9]{4})',
                ]
                for pat in patterns:
                    match = re.search(pat, txt)
                    if match:
                        if len(match.groups()) == 2:
                            time_str = match.group(1)
                            date_str = match.group(2)
                            day, month, year = date_str.split('.')
                            return f"{year}-{month}-{day} {time_str}:00"
                        elif len(match.groups()) == 1:
                            date_str = match.group(1)
                            day, month, year = date_str.split('.')
                            return f"{year}-{month}-{day}"
                match = re.search(r'([0-9]{2}\.[0-9]{2}\.[0-9]{4})', txt)
                if match:
                    day, month, year = match.group(1).split('.')
                    return f"{year}-{month}-{day}"
        return None

    def _looks_like_car_listing(self, element) -> bool:
        """Check if an element looks like a car listing"""
        if not element:
            return False
            
        text = element.get_text().lower()
        
        # Look for indicators that this is a car listing
        car_indicators = [
            'лв',  # Bulgarian leva currency
            'км',  # kilometers
            'обл',  # region (oblast)
            'mercedes', 'bmw', 'audi', 'volkswagen', 'toyota',  # car brands
            'diesel', 'дизел', 'benzin', 'бензин',  # fuel types
        ]
        
        # Element should contain at least 2 car-related indicators
        indicator_count = sum(1 for indicator in car_indicators if indicator in text)
        
        # Also check if element has reasonable amount of text (not just a header)
        has_sufficient_text = len(text.strip()) > 50
        
        return indicator_count >= 2 and has_sufficient_text
    
    def parse_car_item(self, item: Tag) -> Optional[Car]:
        """Parse a single car item and extract car information (robust for mobile.bg real listing structure)"""
        try:
            # Only process divs with class 'item'
            classes = item.get('class', [])
            if 'item' not in classes:
                return None

            # Title and URL
            title_a = item.select_one('a.title')
            if not title_a:
                return None
            title = title_a.get_text(strip=True)
            href = title_a.get('href', '')
            if isinstance(href, list):
                href = href[0] if href else ''
            if isinstance(href, str):
                if href.startswith('//'):
                    listing_url = f"https:{href}"
                elif href.startswith('/'):
                    listing_url = f"{self.BASE_URL}{href}"
                else:
                    listing_url = href
            else:
                listing_url = None

            # Brand, model, year from title
            brand, model, year = self.parse_car_title(title)

            # Price
            price_div = item.select_one('div.price > div')
            price = None
            if price_div:
                price_text = price_div.get_text(strip=True)
                price = self.extract_price(price_text)

            # Parameters (year, km, color, engine, power, etc.)
            params = item.select_one('div.params')
            year_from_params = None
            kilometers = None
            color = None
            engine_type = None
            engine_power = None
            engine_displacement = None
            gearbox_type = None
            doors = None
            seats = None
            if params:
                spans = params.find_all('span')
                for span in spans:
                    txt = span.get_text(strip=True)
                    # Year
                    m = re.search(r'(\d{4})', txt)
                    if m and not year_from_params:
                        year_from_params = int(m.group(1))
                    # Kilometers
                    if 'км' in txt and not kilometers:
                        km = re.sub(r'[^\d]', '', txt)
                        if km:
                            kilometers = int(km)
                    # Color
                    if txt.lower() in ['черен', 'бял', 'сив', 'червен', 'син', 'зелен', 'жълт', 'кафяв', 'оранжев', 'златен', 'лилав', 'розов', 'бежов', 'бордо', 'сребърен']:
                        color = txt
                    # Engine type
                    if txt.lower() in ['дизелов', 'бензинов', 'хибриден', 'електрически']:
                        engine_type = txt
                    # Power
                    if 'к.с.' in txt:
                        p = re.sub(r'[^\d]', '', txt)
                        if p:
                            engine_power = str(p)
                    # Displacement
                    if 'куб' in txt:
                        d = re.sub(r'[^\d]', '', txt)
                        if d:
                            engine_displacement = str(d)
                    # Gearbox
                    if txt.lower() in ['автоматична', 'ръчна']:
                        gearbox_type = txt
                    # Doors/seats (not always present)
                    if 'врати' in txt.lower():
                        doors_val = re.sub(r'[^\d]', '', txt)
                        if doors_val:
                            doors = int(doors_val)
                    if 'места' in txt.lower():
                        seats_val = re.sub(r'[^\d]', '', txt)
                        if seats_val:
                            seats = int(seats_val)

            if not year and year_from_params:
                year = year_from_params

            # Location
            location = None
            seller_loc = item.select_one('div.seller .location')
            if seller_loc:
                location = seller_loc.get_text(strip=True)

            # Dealer name
            dealer_name = None
            dealer = item.select_one('div.seller .name a')
            if dealer:
                dealer_name = dealer.get_text(strip=True)

            # Images
            image_urls = []
            img_tags = item.select('div.photo img.pic')
            for img in img_tags:
                src = img.get('src', '')
                if isinstance(src, list):
                    src = src[0] if src else ''
                if isinstance(src, str):
                    if src.startswith('//'):
                        image_urls.append(f"https:{src}")
                    elif src:
                        image_urls.append(src)

            # Description
            description = None
            info = item.select_one('div.info')
            if info:
                description = info.get_text(strip=True)

            # Only create Car object if we have essential data
            if price and brand != "Unknown":
                car = Car(
                    brand=brand,
                    model=model,
                    year=year,
                    price=price,
                    currency="BGN",
                    kilometers=kilometers,
                    engine_type=engine_type,
                    engine_displacement=engine_displacement,
                    engine_power=engine_power,
                    gearbox_type=gearbox_type,
                    color=color,
                    location=location,
                    dealer_name=dealer_name,
                    source_site="mobile.bg",
                    listing_url=listing_url if isinstance(listing_url, str) else None,
                    image_urls=image_urls,
                    description=description
                )
                return car
            else:
                self.logger.debug(f"Skipping item with insufficient data: price={price}, brand={brand}")
                return None
        except Exception as e:
            self.logger.warning(f"Error parsing car item: {str(e)}")
            return None
    
    def parse_car_title(self, title: str) -> tuple[str, str, Optional[int]]:
        """Parse car title to extract brand, model, and year"""
        # First, try to find year anywhere in the title (including with slashes)
        import re
        year = None
        year_match = re.search(r'\b(19[8-9]\d|20[0-3]\d)\b', title)
        if year_match:
            year = int(year_match.group(1))
        
        # Split by spaces for parsing brand and model
        parts = title.split()
        
        # Default values
        brand = parts[0] if parts else "Unknown"
        model = "Unknown"
        
        if len(parts) > 1:
            # Extract model (everything except brand and year)
            model_parts = []
            for part in parts[1:]:
                # Skip parts that contain the year we found
                if year and str(year) in part:
                    # Remove the year from this part
                    part_without_year = re.sub(rf'\b{year}\b', '', part)
                    # Clean up any remaining slashes or empty parts
                    part_without_year = re.sub(r'/+', '/', part_without_year).strip('/')
                    if part_without_year:
                        model_parts.append(part_without_year)
                else:
                    # Also check if this part is just a standalone year
                    if not (part.isdigit() and len(part) == 4 and 1980 <= int(part) <= 2030):
                        model_parts.append(part)
            
            if model_parts:
                model = " ".join(model_parts)
        
        return brand, model, year
    
    def extract_price(self, text: str) -> Optional[int]:
        """Extract price from text"""
        # Look for price patterns like "25000 лв." or "EUR 15000"
        price_patterns = [
            r'(\d+(?:\s*\d+)*)\s*лв',
            r'(\d+(?:\s*\d+)*)\s*BGN',
            r'EUR\s*(\d+(?:\s*\d+)*)',
            r'€\s*(\d+(?:\s*\d+)*)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(' ', '')
                try:
                    return int(price_str)
                except ValueError:
                    continue
        
        return None
    
    def extract_kilometers(self, text: str) -> Optional[int]:
        """Extract kilometers from text"""
        # Look for km patterns, including those in parentheses like "(39 000 км)"
        km_patterns = [
            r'\((\d+(?:\s*\d+)*)\s*км\)',  # Pattern for "(39 000 км)"
            r'(\d+(?:\s*\d+)*)\s*км',
            r'(\d+(?:\s*\d+)*)\s*km',
        ]
        
        for pattern in km_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                km_str = match.group(1).replace(' ', '')
                try:
                    return int(km_str)
                except ValueError:
                    continue
        
        return None
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location from text"""
        # Handle format like "обл. Бургас 18:36 часа на 26.07"
        if 'обл.' in text:
            # Extract the part between 'обл.' and timestamp
            parts = text.split('обл.')
            if len(parts) > 1:
                location_part = parts[1].strip()
                # Remove timestamp (everything after digits followed by colon)
                location_match = re.match(r'^([^0-9:]+)', location_part)
                if location_match:
                    return f"обл. {location_match.group(1).strip()}"
        
        # Common Bulgarian cities and regions
        cities = [
            'софия', 'пловдив', 'варна', 'бургас', 'стара загора', 'плевен',
            'софия-град', 'софия-област', 'благоевград', 'видин', 'враца',
            'габрово', 'добрич', 'кърджали', 'кюстендил', 'ловеч', 'монтана',
            'пазарджик', 'перник', 'разград', 'русе', 'силистра', 'сливен',
            'смолян', 'търговище', 'хасково', 'шумен', 'ямбол'
        ]
        
        text_lower = text.lower()
        for city in cities:
            if city in text_lower:
                return city.title()
        
        # Return first part before timestamp as fallback
        timestamp_match = re.search(r'\d{1,2}:\d{2}', text)
        if timestamp_match:
            return text[:timestamp_match.start()].strip()
        
        return text.strip() if text.strip() else None
