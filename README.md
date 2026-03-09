# fast-flights

A fast, robust Google Flights scraper (API) implemented in Python. Supports flight search and price calendar APIs.

## Installation

```bash
pip install fast-flights
```

## Features

- **Flight Search**: Search for flights with flexible filters via `get_flights()`
- **Price Calendar Grid**: Get 2D price matrix for departure/return date ranges
- **Price Calendar Graph**: Get prices for fixed trip duration across a date range

## Quick Start

### Search Flights

```python
from fast_flights import FlightQuery, Passengers, create_query, get_flights

query = create_query(
    flights=[
        FlightQuery(date="2026-05-28", from_airport="FRA", to_airport="TAO", max_stops=1)
    ],
    passengers=Passengers(adults=1),
    currency="EUR",
)

result = get_flights(query)

for flight in result:
    stops = len(flight.flights) - 1
    print(f"{flight.price} EUR - {stops} stops")
    for leg in flight.flights:
        print(f"  {leg.from_airport.code} -> {leg.to_airport.code}")
```

### Price Calendar Grid (2D Matrix)

Get prices for all combinations of departure and return dates:

```python
from fast_flights import get_calendar_grid

calendar = get_calendar_grid(
    from_airport="FRA",
    to_airport="TAO",
    departure_range=("2026-04-28", "2026-05-05"),
    return_range=("2026-05-20", "2026-05-31"),
    max_stops=1,                    # 0=nonstop, 1=1 stop, 2=2+ stops, None=any
    max_duration=1080,              # max flight duration in minutes (18 hours)
    bags=(1, 0),                    # (checked_bags, carry_on)
    outbound_times=(6, 22, 0, 24),  # (earliest_dep, latest_dep, earliest_arr, latest_arr)
    separate_tickets=True,          # allow separate tickets
    currency="EUR",
)

cheapest = calendar.cheapest()
print(f"Cheapest: {cheapest.outbound_date} -> {cheapest.return_date}: {cheapest.price} {cheapest.currency}")
```

### Price Calendar Graph (Fixed Duration)

Get prices for a fixed trip duration across a date range:

```python
from fast_flights import get_calendar_graph

calendar = get_calendar_graph(
    from_airport="FRA",
    to_airport="TAO",
    date_range=("2026-05-01", "2026-06-30"),
    trip_duration=14,               # 14-day trip
    max_stops=1,
    max_duration=1080,
    outbound_times=(6, 22, 0, 24),
    return_times=(6, 22, 0, 24),
    separate_tickets=True,
    currency="EUR",
)

cheapest = calendar.cheapest()
print(f"Cheapest 2-week trip: depart {cheapest.outbound_date}: {cheapest.price} {cheapest.currency}")
```

### Using City MIDs

You can also search by city (using Google's MID identifiers) instead of airport codes:

```python
from fast_flights import get_calendar_grid

calendar = get_calendar_grid(
    from_city="/m/02z0j",   # Shanghai
    to_city="/m/01l3s0",    # Beijing
    departure_range=("2026-04-25", "2026-05-01"),
    return_range=("2026-05-21", "2026-05-22"),
)
```

### Generate Google Flights URL

Generate a shareable Google Flights search URL:

```python
from fast_flights import FlightQuery, Passengers, create_query

# One-way
query = create_query(
    flights=[FlightQuery(date="2026-05-28", from_airport="FRA", to_airport="TAO", max_stops=1)],
    passengers=Passengers(adults=1),
    currency="EUR",
)
print(query.url())
# https://www.google.com/travel/flights/search?tfs=...&curr=EUR

# Round-trip
query = create_query(
    flights=[
        FlightQuery(date="2026-05-28", from_airport="FRA", to_airport="TAO", max_stops=1),
        FlightQuery(date="2026-06-17", from_airport="TAO", to_airport="FRA", max_stops=1),
    ],
    trip="round-trip",
    passengers=Passengers(adults=1),
    currency="EUR",
)
print(query.url())
```

Query object methods:
- `query.url()` - Full Google Flights search URL
- `query.params()` - Dictionary of URL parameters
- `query.to_str()` - Base64-encoded tfs parameter

## API Reference

### `get_calendar_grid()`

Returns a 2D grid of prices for all combinations of departure and return dates.

| Parameter | Type | Description |
|-----------|------|-------------|
| `from_airport` | `str` | Departure airport code (e.g., "FRA") |
| `to_airport` | `str` | Arrival airport code (e.g., "TAO") |
| `from_city` | `str` | Departure city MID (alternative to airport) |
| `to_city` | `str` | Arrival city MID (alternative to airport) |
| `departure_range` | `tuple[str, str]` | (start_date, end_date) for departures |
| `return_range` | `tuple[str, str]` | (start_date, end_date) for returns |
| `adults` | `int` | Number of adults (default: 1) |
| `children` | `int` | Number of children (default: 0) |
| `seat_class` | `int` | 1=economy, 2=premium, 3=business, 4=first |
| `max_stops` | `int \| None` | None=any, 0=nonstop, 1=1 stop, 2=2+ stops |
| `max_duration` | `int \| None` | Max flight duration in minutes |
| `bags` | `tuple[int, int] \| None` | (checked_bags, carry_on) |
| `outbound_times` | `tuple[int, int, int, int] \| None` | (earliest_dep, latest_dep, earliest_arr, latest_arr) in hours 0-24 |
| `return_times` | `tuple[int, int, int, int] \| None` | Same format for return flight |
| `separate_tickets` | `bool` | Allow separate tickets (default: False) |
| `currency` | `str` | Currency code (default: "USD") |
| `language` | `str` | Language code (default: "en") |

### `get_calendar_graph()`

Returns prices for a fixed trip duration across a date range.

Same parameters as `get_calendar_grid()`, plus:

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_range` | `tuple[str, str]` | (start_date, end_date) for departures |
| `trip_duration` | `int` | Fixed trip duration in days |

### `PriceCalendar`

Result object with helper methods:

```python
calendar.entries          # List of CalendarEntry objects
calendar.cheapest()       # Get cheapest entry
calendar.most_expensive() # Get most expensive entry
calendar.by_outbound_date("2026-05-01")  # Filter by outbound date
calendar.by_return_date("2026-05-15")    # Filter by return date
```

### `CalendarEntry`

```python
entry.outbound_date  # "2026-05-01"
entry.return_date    # "2026-05-15"
entry.price          # 450.0
entry.currency       # "EUR"
```

## Dependencies

- `curl_cffi` - Browser impersonation for requests
- `protobuf` - Protocol buffer support
- `selectolax` - HTML parsing
- `primp` - HTTP client

## License

MIT License
