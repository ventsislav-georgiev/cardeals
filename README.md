# Car Deals CLI

A Python command-line tool that scrapes car listings from mobile.bg based on your search criteria and returns results in JSON format.

## Features

- ✅ Scrapes: mobile.bg
- 🔍 Advanced filtering by brand, model, year, price, mileage, engine type, gearbox
- 📄 Clean JSON output with detailed car information
- 🚀 Fast concurrent scraping with intelligent rate limiting
- 🛡️ Robust error handling and retry mechanisms
- 📝 Comprehensive logging and debugging support
- 🧪 Full test coverage

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd cardeals
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python cardeals.py --brand Mercedes --model GLC
```

### Save to File

```bash
python cardeals.py --brand BMW --model X5 --output results.json
```

## Command Line Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--brand` | String | ✅ | Car brand (Mercedes, BMW, Audi, etc.) |
| `--model` | String | ✅ | Car model (GLC, X5, A4, etc.) |
| `--year-start` | Integer | ❌ | Minimum manufacturing year |
| `--price-max` | Integer | ❌ | Maximum price in EUR |
| `--km-max` | Integer | ❌ | Maximum mileage in kilometers |
| `--engine-type` | Choice | ❌ | Engine type: petrol, diesel, hybrid, electric |
| `--gearbox-type` | Choice | ❌ | Gearbox type: manual, automatic |
| `--output` | String | ❌ | Output file path (default: stdout) |
| `--verbose` | Flag | ❌ | Enable verbose logging |
| `--max-pages` | Integer | ❌ | Maximum pages to scrape (default: 10) |

## Testing

Run the comprehensive test suite:

```bash
python test_scrapers.py
```

The test suite includes:
- Unit tests for both scrapers
- Integration tests with real data
- URL building and parsing validation
- Error handling verification

## Supported Sites

- **mobile.bg** - Bulgarian car marketplace

Both sites support the same search parameters and return data in the same format.

## Project Structure

- `cardeals.py` - Main CLI application
- `scrapers/base.py` - Abstract base scraper with common functionality  
- `scrapers/mobile_bg.py` - mobile.bg specific scraper
- `models/car.py` - Car data model for consistent representation
- `utils/logger.py` - Logging utilities
- `tests/` - Comprehensive test suite

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the test suite: `python -m pytest tests/`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
