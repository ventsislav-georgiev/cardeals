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
        """Parse a listing page and extract car information"""
        cars = []
        try:
            # Try common mobile.bg selectors for car listings
            selectors = [
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
            # Remove duplicates
            items = list(dict.fromkeys(items))
            if not items:
                # Fallback: look for any div that looks like a car listing
                all_divs = soup.find_all('div')
                items = [div for div in all_divs if self._looks_like_car_listing(div)]
            self.logger.info(f"[mobile.bg] Found {len(items)} car listing divs on page {page_num}")
            # Print first 3 titles for debug
            for i, item in enumerate(items[:3]):
                title = item.get_text(strip=True)[:120]
                self.logger.info(f"[mobile.bg] Example listing {i+1}: {title}")
            # Filter out divs with class 'resultsInfoBox'
            filtered_items = [item for item in items if not (
                'resultsInfoBox' in item.get('class', []) or
                'paramsFromSearchText' in item.get('class', []) or
                item.get('id', '') == 'paramsFromSearchText'
            )]
            # Save the HTML of the first 5 filtered divs for inspection
            if filtered_items:
                try:
                    with open("debug_first_listing.html", "w", encoding="utf-8") as f:
                        for i, div in enumerate(filtered_items[:5]):
                            f.write(f"\n<!-- Listing Candidate {i+1} -->\n")
                            f.write(str(div))
                            f.write("\n\n")
                    self.logger.info("[mobile.bg] Saved first 5 real car listing candidates to debug_first_listing.html")
                except Exception as e:
                    self.logger.warning(f"[mobile.bg] Could not save debug_first_listing.html: {e}")
            # Use filtered_items for parsing
            items = filtered_items
            if not items:
                # Print first 10 divs' class names and text snippets for debugging (stdout)
                all_divs = soup.find_all('div')
                print("\n[DEBUG] First 10 <div> elements on the page (full HTML):", flush=True)
                for i, div in enumerate(all_divs[:10]):
                    print(f"[DEBUG] DIV {i+1} HTML:\n{div.prettify()[:800]}\n{'-'*60}", flush=True)
            for item in items:
                try:
                    car = self.parse_car_item(item)
                    if car:
                        cars.append(car)
                except Exception as e:
                    self.logger.warning(f"Error parsing car item: {str(e)}")
                    continue
        except Exception as e:
            self.logger.error(f"Error parsing listing page {page_num}: {str(e)}")
        # Deduplicate by listing_url
        unique = {}
        for car in cars:
            if car.listing_url and car.listing_url not in unique:
                unique[car.listing_url] = car
        deduped_cars = list(unique.values())
        self.logger.info(f"[mobile.bg] Successfully parsed {len(deduped_cars)} unique cars from page {page_num}")
        return deduped_cars
    
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
        parts = title.split()
        
        # Default values
        brand = parts[0] if parts else "Unknown"
        model = "Unknown"
        year = None
        
        if len(parts) > 1:
            # Look for year (4-digit number)
            year_indices = []
            for i, part in enumerate(parts):
                if part.isdigit() and len(part) == 4:
                    year_candidate = int(part)
                    if 1980 <= year_candidate <= 2030:
                        year = year_candidate
                        year_indices.append(i)
                        break
            
            # Build model from remaining parts (excluding brand and year)
            model_parts = []
            for i, part in enumerate(parts[1:], 1):
                if i not in year_indices:
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
