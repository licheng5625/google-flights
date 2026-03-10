# Google Flights Search

Fast, robust Google Flights scraper (API) for searching flights and price calendars.

## Features

- ✈️ **Flight Search**: Search flights with flexible filters
- 📅 **Price Calendar Grid**: 2D price matrix for departure/return date ranges
- 📊 **Price Calendar Graph**: Prices for fixed trip duration across dates

## Installation

```bash
# Install dependencies
pip install protobuf curl_cffi selectolax primp

# Or using requirements.txt
pip install -r requirements.txt
```

## Usage

### 1. Search Flights

```bash
python3 /config/nanobot/workspace/skills/google-flights/skill/search_flights.py \
  --from FRA \
  --to PVG \
  --departure 2026-05-01 \
  --return 2026-05-15 \
  --adults 1 \
  --currency EUR
```

### 2. Price Calendar Grid (2D Matrix)

Get prices for all combinations of departure and return dates:

```bash
python3 /config/nanobot/workspace/skills/google-flights/skill/calendar_grid.py \
  --from FRA \
  --to TAO \
  --departure-range 2026-04-28 2026-05-05 \
  --return-range 2026-05-20 2026-05-31 \
  --max-stops 1 \
  --currency EUR
```

### 3. Price Calendar Graph (Fixed Duration)

Get prices for a fixed trip duration:

```bash
python3 /config/nanobot/workspace/skills/google-flights/skill/calendar_graph.py \
  --from FRA \
  --to TAO \
  --date-range 2026-05-01 2026-06-30 \
  --duration 14 \
  --max-stops 1 \
  --currency EUR
```

## Parameters

### Common Parameters

- `--from` / `--from-city`: Departure airport code or city MID
- `--to` / `--to-city`: Arrival airport code or city MID
- `--adults`: Number of adults (default: 1)
- `--children`: Number of children (default: 0)
- `--seat-class`: 1=economy, 2=premium, 3=business, 4=first
- `--max-stops`: None=any, 0=nonstop, 1=1 stop, 2=2+ stops
- `--max-duration`: Max flight duration in minutes
- `--currency`: Currency code (default: EUR)
- `--language`: Language code (default: en)

### Advanced Filters

- `--bags`: Checked bags and carry-on (e.g., `1 0`)
- `--outbound-times`: Departure time window (e.g., `6 22 0 24`)
- `--return-times`: Return time window (e.g., `6 22 0 24`)
- `--separate-tickets`: Allow separate tickets

## Examples

### Find cheapest flight to Beijing

```bash
python3 /config/nanobot/workspace/skills/google-flights/skill/search_flights.py \
  --from FRA \
  --to PEK \
  --departure 2026-05-01 \
  --return 2026-05-15 \
  --adults 2 \
  --currency EUR
```

### Find best 2-week vacation dates

```bash
python3 /config/nanobot/workspace/skills/google-flights/skill/calendar_graph.py \
  --from FRA \
  --to TAO \
  --date-range 2026-05-01 2026-06-30 \
  --duration 14 \
  --max-stops 1 \
  --currency EUR
```

### Compare prices for flexible dates

```bash
python3 /config/nanobot/workspace/skills/google-flights/skill/calendar_grid.py \
  --from FRA \
  --to PVG \
  --departure-range 2026-04-28 2026-05-05 \
  --return-range 2026-05-20 2026-05-31 \
  --max-stops 1 \
  --currency EUR
```

## Output Format

All scripts output JSON with flight information:

```json
{
  "success": true,
  "entries": [
    {
      "outbound_date": "2026-05-01",
      "return_date": "2026-05-15",
      "price": 475.0,
      "currency": "EUR"
    }
  ],
  "cheapest": {
    "outbound_date": "2026-05-01",
    "return_date": "2026-05-15",
    "price": 475.0,
    "currency": "EUR"
  }
}
```

## City MID Codes

Use Google's MID identifiers for city-level search:

- Shanghai: `/m/02z0j`
- Beijing: `/m/01l3s0`
- Frankfurt: `/m/02_286`
- Munich: `/m/0f2v0`

## Notes

- Dates must be in `YYYY-MM-DD` format
- Times are in 24-hour format (0-24)
- Duration is in minutes for `--max-duration`
- Duration is in days for `--duration` (calendar graph)
- All prices are approximate and may change

## Repository

https://github.com/AirP0WeR/google-flights
