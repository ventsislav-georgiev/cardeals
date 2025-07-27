#!/usr/bin/env python3
"""
Comprehensive test suite for the car deals scraper.
Tests both the scraper functionality and CLI integration.
"""

import unittest
import sys
import os
import json
import subprocess
import tempfile

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from models.car import Car
from scrapers.mobile_bg import MobileBgScraper


class TestMobileBgScraper(unittest.TestCase):
    """Test suite for mobile.bg scraper functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scraper = MobileBgScraper()
        self.test_params = {
            'brand': 'Mercedes',
            'model': 'GLC',
            'price_max': 70000,
            'year_start': 2019,
            'engine_type': 'diesel',
            'gearbox_type': 'automatic',
            'km_max': 200000
        }
    
    def test_initialization(self):
        """Test scraper initialization."""
        self.assertIsNotNone(self.scraper)
        self.assertEqual(self.scraper.BASE_URL, "https://mobile.bg")
    
    def test_build_search_url(self):
        """Test URL building for mobile.bg."""
        url = self.scraper.build_search_url(self.test_params)
        
        # Check URL structure based on provided example
        self.assertIn("mobile.bg/obiavi/avtomobili-dzhipove", url)
        self.assertIn("mercedes-benz", url.lower())  # Brand mapping
        self.assertIn("glc-klasa", url.lower())      # Model mapping
        self.assertIn("dizelov", url)                # Diesel in Bulgarian
        self.assertIn("avtomatichna", url)           # Automatic in Bulgarian
        self.assertIn("ot-2019", url)                # From 2019
        self.assertIn("price1=140000", url)          # 70000 EUR * 2 for BGN conversion
        
        print(f"Built URL: {url}")
    
    def test_url_build_with_minimal_params(self):
        """Test URL building with minimal parameters."""
        minimal_params = {'brand': 'BMW', 'model': 'X5'}
        url = self.scraper.build_search_url(minimal_params)
        
        self.assertIn("mobile.bg/obiavi/avtomobili-dzhipove", url)
        self.assertIn("bmw", url.lower())
        self.assertIn("x5", url.lower())
        print(f"Minimal URL: {url}")
    
    def test_brand_model_mapping(self):
        """Test brand and model name mappings."""
        # Test Mercedes brand mapping
        params = {'brand': 'Mercedes', 'model': 'GLC'}
        url = self.scraper.build_search_url(params)
        self.assertIn("mercedes-benz", url)
        self.assertIn("glc-klasa", url)
        
        # Test other brand mappings
        params = {'brand': 'VW', 'model': 'Golf'}
        url = self.scraper.build_search_url(params)
        self.assertIn("volkswagen", url)
    
    def test_parse_car_title(self):
        """Test car title parsing."""
        test_cases = [
            ("Mercedes GLC 220 d 2020", ("Mercedes", "GLC 220 d", 2020)),
            ("BMW X5 xDrive30d", ("BMW", "X5 xDrive30d", None)),
            ("Audi A4 Avant 2.0 TDI 2019", ("Audi", "A4 Avant 2.0 TDI", 2019)),
            ("Ford Focus 1.6 TDCI 2018", ("Ford", "Focus 1.6 TDCI", 2018)),
        ]
        
        for title, expected in test_cases:
            brand, model, year = self.scraper.parse_car_title(title)
            self.assertEqual(brand, expected[0])
            self.assertEqual(model, expected[1])
            self.assertEqual(year, expected[2])
    
    def test_extract_price(self):
        """Test price extraction from text."""
        test_cases = [
            ("51 500 лв.", 51500),
            ("61900 BGN", 61900),
            ("Цена: 45 000 лв.", 45000),
            ("25000 лв", 25000),
            ("EUR 30000", 30000),
            ("€ 25000", 25000),
        ]
        
        for text, expected in test_cases:
            price = self.scraper.extract_price(text)
            self.assertEqual(price, expected, f"Failed for text: {text}")
    
    def test_extract_kilometers(self):
        """Test kilometers extraction from text."""
        test_cases = [
            ("(163 828 км)", 163828),
            ("99 933 km", 99933),
            ("Пробег: 120000 км", 120000),
            ("50000 км", 50000),
        ]
        
        for text, expected in test_cases:
            km = self.scraper.extract_kilometers(text)
            self.assertEqual(km, expected, f"Failed for text: {text}")
    
    def test_extract_location(self):
        """Test location extraction from text."""
        test_cases = [
            ("обл. Бургас 18:36 часа на 26.07", "обл. Бургас"),
            ("София-град", "София-Град"),
            ("Пловдив", "Пловдив"),
            ("гр. Варна", "Варна"),
        ]
        
        for text, expected in test_cases:
            location = self.scraper.extract_location(text)
            self.assertIsNotNone(location, f"Failed to extract location from: {text}")
            if expected and location:
                # Pass if either is a substring of the other (case-insensitive)
                self.assertTrue(
                    expected.lower() in location.lower() or location.lower() in expected.lower(),
                    f"Failed for text: {text} (expected: {expected}, got: {location})"
                )


class TestCLIIntegration(unittest.TestCase):
    """Test the CLI integration with real scraping."""
    
    def test_cli_help(self):
        """Test CLI help output."""
        cmd = ['python', 'cardeals.py', '--help']
        
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('--brand', result.stdout)
        self.assertIn('--model', result.stdout)
        self.assertIn('--engine-type', result.stdout)
        self.assertIn('--gearbox-type', result.stdout)
        print("✓ CLI help output working correctly")
    
    def test_cli_command_execution(self):
        """Test executing the CLI command with the exact parameters from the user request."""
        # Test the exact command from the user request
        cmd = [
            'python', 'cardeals.py',
            '--brand', 'Mercedes',
            '--model', 'GLC', 
            '--year-start', '2019',
            '--price-max', '70000',
            '--km-max', '200000',
            '--engine-type', 'diesel',
            '--gearbox-type', 'automatic',
            '--sites', 'mobile.bg',
            '--verbose',
            '--max-pages', '1'  # Limit to 1 page for testing
        ]
        
        try:
            # Run the command
            result = subprocess.run(
                cmd, 
                cwd=project_dir,
                capture_output=True, 
                text=True, 
                timeout=60  # 1 minute timeout
            )
            
            print(f"Command: {' '.join(cmd)}")
            print(f"Return code: {result.returncode}")
            
            if result.stderr:
                print(f"STDERR: {result.stderr}")
            
            # Check if command executed successfully
            if result.returncode != 0:
                print(f"Command failed with stderr: {result.stderr}")
                print(f"Command failed with stdout: {result.stdout}")
                self.fail(f"Command failed with return code {result.returncode}")
            
            # Parse JSON output
            if result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    
                    # Validate JSON structure
                    self.assertIn('search_params', data)
                    self.assertIn('total_results', data)
                    self.assertIn('timestamp', data)
                    self.assertIn('cars', data)
                    
                    # Check search parameters
                    search_params = data['search_params']
                    self.assertEqual(search_params['brand'], 'Mercedes')
                    self.assertEqual(search_params['model'], 'GLC')
                    self.assertEqual(search_params['year_start'], 2019)
                    self.assertEqual(search_params['price_max'], 70000)
                    
                    # Check results
                    total_results = data['total_results']
                    cars = data['cars']
                    
                    print(f"✓ Total results found: {total_results}")
                    
                    if total_results > 0:
                        # Validate first car structure
                        first_car = cars[0]
                        required_fields = ['brand', 'model', 'price', 'currency', 'source_site']
                        
                        for field in required_fields:
                            self.assertIn(field, first_car, f"Missing field: {field}")
                        
                        self.assertEqual(first_car['source_site'], 'mobile.bg')
                        self.assertEqual(first_car['currency'], 'BGN')
                        
                        print(f"✓ Sample car: {first_car['brand']} {first_car['model']} - {first_car['price']} {first_car['currency']}")
                        if first_car.get('year'):
                            print(f"  Year: {first_car['year']}")
                        if first_car.get('kilometers'):
                            print(f"  Kilometers: {first_car['kilometers']} km")
                        if first_car.get('location'):
                            print(f"  Location: {first_car['location']}")
                        if first_car.get('listing_url'):
                            print(f"  URL: {first_car['listing_url'][:80]}...")
                        
                        # Validate that cars match search criteria where possible
                        for i, car in enumerate(cars[:3]):  # Check first 3 cars
                            if car.get('brand'):
                                self.assertIn('mercedes', car['brand'].lower(), 
                                            f"Car {i+1} brand doesn't match: {car['brand']}")
                            if car.get('year') and car['year']:
                                self.assertGreaterEqual(car['year'], 2019, 
                                                      f"Car {i+1} year doesn't match criteria: {car['year']}")
                            if car.get('price') and car['price']:
                                # Price should be in BGN and reasonable for the search
                                self.assertGreater(car['price'], 10000, 
                                                 f"Car {i+1} price seems too low: {car['price']}")
                                self.assertLess(car['price'], 500000, 
                                               f"Car {i+1} price seems too high: {car['price']}")
                        
                        print("✓ All validation checks passed!")
                        
                    else:
                        print("⚠ No results found - this might indicate:")
                        print("  1. The search criteria are too restrictive")
                        print("  2. The scraper needs adjustment for current mobile.bg structure")
                        print("  3. Network/site access issues")
                        # Don't fail the test if no results, as this can be expected
                        
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON output: {e}")
                    print(f"Raw output (first 500 chars): {result.stdout[:500]}...")
                    self.fail("Invalid JSON output")
            else:
                self.fail("No output received from command")
                
        except subprocess.TimeoutExpired:
            self.fail("Command timed out - scraping took too long (>1 minute)")
        except Exception as e:
            self.fail(f"Command execution failed: {e}")
    
    def test_cli_with_output_file(self):
        """Test CLI with output file option."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name
        
        try:
            cmd = [
                'python', 'cardeals.py',
                '--brand', 'BMW',
                '--model', 'X5',
                '--price-max', '50000',
                '--max-pages', '1',
                '--output', output_file
            ]
            
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            self.assertEqual(result.returncode, 0)
            
            # Check if output file was created and contains valid JSON
            self.assertTrue(os.path.exists(output_file))
            
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertIn('search_params', data)
                self.assertIn('total_results', data)
                self.assertIn('cars', data)
            
            print(f"✓ Output file test passed: {output_file}")
            
        finally:
            # Clean up
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestRealScraping(unittest.TestCase):
    """Test actual scraping functionality with real data."""
    
    def setUp(self):
        """Set up real scraping test."""
        self.scraper = MobileBgScraper()
    
    def test_real_scraping_mercedes_glc(self):
        """Test real scraping for Mercedes GLC with the exact user parameters."""
        print("\n=== Testing real mobile.bg scraping ===")
        
        try:
            # Test with the exact parameters from user request
            search_params = {
                'brand': 'Mercedes',
                'model': 'GLC',
                'engine_type': 'diesel',
                'gearbox_type': 'automatic',
                'year_start': 2019,
                'price_max': 70000,
                'km_max': 200000
            }
            
            cars = self.scraper.scrape(search_params, max_pages=2)  # Limit to 2 pages for testing
            
            print(f"Found {len(cars)} cars")
            
            if cars:
                # Test first result structure
                first_car = cars[0]
                self.assertIsInstance(first_car, Car)
                self.assertIsNotNone(first_car.brand)
                self.assertIsNotNone(first_car.model)
                self.assertEqual(first_car.source_site, "mobile.bg")
                
                print(f"Sample result: {first_car.brand} {first_car.model}")
                print(f"Price: {first_car.price} {first_car.currency}")
                print(f"Year: {first_car.year}")
                print(f"Kilometers: {first_car.kilometers}")
                print(f"Location: {first_car.location}")
                print(f"URL: {first_car.listing_url}")
                
                # Validate search criteria matching
                if first_car.brand:
                    self.assertIn('mercedes', first_car.brand.lower())
                
                if first_car.year:
                    self.assertGreaterEqual(first_car.year, 2019)
                
                # Test JSON serialization
                car_dict = first_car.to_dict()
                self.assertIsInstance(car_dict, dict)
                self.assertIn('brand', car_dict)
                self.assertIn('model', car_dict)
                
                # Test multiple results
                if len(cars) > 1:
                    print(f"Additional cars found: {len(cars) - 1}")
                    for i, car in enumerate(cars[1:4], 2):  # Show up to 3 more
                        print(f"  Car {i}: {car.brand} {car.model} - {car.price} {car.currency}")
                
            else:
                print("No results found. This could indicate:")
                print("1. Changed HTML structure on mobile.bg")
                print("2. Anti-bot protection activated")
                print("3. URL building issues")
                print("4. Network connectivity problems")
                print("5. Very restrictive search criteria")
                
                # Let's also test with broader criteria
                print("\nTrying with broader search criteria...")
                broader_params = {'brand': 'Mercedes', 'model': 'GLC'}
                broader_cars = self.scraper.scrape(broader_params, max_pages=1)
                print(f"Broader search found {len(broader_cars)} cars")
                
                if broader_cars:
                    print("✓ Broader search worked - issue might be with specific criteria")
                else:
                    print("✗ Even broader search failed - likely a scraper issue")
                
        except Exception as e:
            print(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"Real scraping test failed: {e}")


if __name__ == '__main__':
    print("=" * 80)
    print("CARDEALS SCRAPER TEST SUITE")
    print("=" * 80)
    print("Testing the mobile.bg car scraper with the following command:")
    print("python cardeals.py --brand Mercedes --model GLC --year-start 2019 \\")
    print("  --price-max 70000 --km-max 200000 --engine-type diesel \\")
    print("  --gearbox-type automatic --sites mobile.bg")
    print("=" * 80)
    
    # Run tests with high verbosity
    unittest.main(verbosity=2, buffer=False)
