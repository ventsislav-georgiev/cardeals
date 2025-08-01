# Car Deals CLI

A Python command-line tool that scrapes car listings from mobile.bg based on your search criteria and returns results in JSON format.

## Features

- ✅ Scrapes: mobile.bg
- 🔍 Advanced filtering by brand, model, year, price, mileage, engine type, gearbox
- 📄 Clean JSON output with detailed car information

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

## Supported Sites

- **mobile.bg** - Bulgarian car marketplace

## License

MIT License
