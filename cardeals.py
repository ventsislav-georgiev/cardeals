#!/usr/bin/env python3
"""
Car Deals CLI - Mobile.bg focused scraper
Scrapes car listings from mobile.bg based on search criteria.
"""


import sys
import os
import json
import time
import click

# DB helper
from utils import db as cardb

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from models.car import Car
from scrapers.mobile_bg import MobileBgScraper


@click.command()
@click.option('--brand', required=False, help='Car brand (e.g., Mercedes, BMW, Audi)')
@click.option('--model', help='Car model (e.g., GLC, X5, A4)')
@click.option('--year-start', type=int, help='Minimum year')
@click.option('--price-max', type=int, help='Maximum price in EUR')
@click.option('--km-max', type=int, help='Maximum kilometers')
@click.option('--engine-type', type=click.Choice(['petrol', 'diesel', 'hybrid', 'electric']), help='Engine type')
@click.option('--gearbox-type', type=click.Choice(['manual', 'automatic']), help='Gearbox type')
@click.option('--sites', type=click.Choice(['mobile.bg']), default='mobile.bg', help='Site to scrape (only mobile.bg supported)')
@click.option('--output', help='Output file (default: stdout)')
@click.option('--verbose', is_flag=True, help='Verbose output')
@click.option('--max-pages', type=int, default=10, help='Maximum pages to scrape')
# New DB-related flags
@click.option('--use-db', is_flag=True, help='Store/update cars in local SQLite DB')
@click.option('--clear-db', is_flag=True, help='Clear the local SQLite DB and exit')
@click.option('--print-db', is_flag=True, help='Print all cars from DB and exit (no scraping)')
def main(brand, model, year_start, price_max, km_max, engine_type, gearbox_type, sites, output, verbose, max_pages, use_db, clear_db, print_db):
    """
    Scrape car listings from mobile.bg based on search criteria.
    
    Examples:
        python cardeals.py --brand Mercedes --model GLC --year-start 2019 --price-max 70000 --km-max 200000 --engine-type diesel --gearbox-type automatic --sites mobile.bg
        
        python cardeals.py --brand BMW --model X5 --price-max 50000 --verbose
    """
    

    # DB: clear and exit
    if clear_db:
        cardb.clear_db()
        click.echo("[INFO] Database cleared.")
        sys.exit(0)

    # DB: print and exit
    if print_db:
        import datetime
        cardb.init_db()
        rows = cardb.get_all_cars()
        cars = []
        for row in rows:
            try:
                car_dict = json.loads(row['data'])
            except Exception:
                car_dict = {}
            car_dict['status'] = row['status']
            car_dict['last_seen'] = row['last_seen']
            car_dict['removed_date'] = row['removed_date']
            car_dict['created_date'] = row['created_date']
            cars.append(car_dict)
        results = {
            'search_params': {},
            'search_url': None,
            'total_results': len(cars),
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'cars': cars
        }
        json_output = json.dumps(results, indent=2, ensure_ascii=False)
        click.echo(json_output)
        sys.exit(0)

    # Normal scraping flow
    if not brand:
        click.echo("❌ Error: --brand is required unless --print-db or --clear-db is used.", err=True)
        sys.exit(1)

    scraper = MobileBgScraper(verbose=verbose)

    # Prepare search parameters
    search_params = {
        'brand': brand,
        'model': model,
        'year_start': year_start,
        'price_max': price_max,
        'km_max': km_max,
        'engine_type': engine_type,
        'gearbox_type': gearbox_type,
    }
    search_params = {k: v for k, v in search_params.items() if v is not None}

    search_url = scraper.build_search_url(search_params)
    if verbose:
        click.echo(f"[INFO] Search URL: {search_url}", err=True)
        click.echo(f"🚗 Starting car search for {brand} {model or ''}", err=True)

    try:
        cars = scraper.scrape(search_params, max_pages)

        # Deduplicate by listing_url globally
        unique = {}
        for car in cars:
            if car.listing_url and car.listing_url not in unique:
                unique[car.listing_url] = car
        deduped_cars = list(unique.values())

        if verbose:
            click.echo(f"INFO - Completed scraping. Total unique cars found: {len(deduped_cars)}", err=True)

        # DB logic
        if use_db:
            cardb.init_db()
            # Store/update all found cars
            for car in deduped_cars:
                cardb.upsert_car(car.listing_url, json.dumps(car.to_dict(), ensure_ascii=False), status='active', created_date=car.created_date)
            # Mark as removed any cars in DB that are not in current scrape
            db_links = set(row['link'] for row in cardb.get_all_cars())
            scraped_links = set(car.listing_url for car in deduped_cars if car.listing_url)
            removed_links = db_links - scraped_links
            for link in removed_links:
                cardb.mark_removed(link)
            if verbose:
                click.echo(f"[DB] Updated {len(deduped_cars)} cars, marked {len(removed_links)} as removed.", err=True)

        results = {
            'search_params': search_params,
            'search_url': search_url,
            'total_results': len(deduped_cars),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'cars': [car.to_dict() for car in deduped_cars]
        }

        json_output = json.dumps(results, indent=2, ensure_ascii=False)

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            if verbose:
                click.echo(f"✅ Results saved to {output}", err=True)
        else:
            click.echo(json_output)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
