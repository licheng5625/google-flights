"""Google Flights Shopping API - Alternative API using JSON encoding.

This module uses the GetShoppingResults API endpoint which accepts JSON-encoded
filters instead of Protobuf. This is simpler and more reliable than the
Calendar API.
"""

import base64
import json
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    from primp import Client

from .fetcher import CONSENT_COOKIE

SHOPPING_URL = "https://www.google.com/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/GetShoppingResults"


@dataclass
class ShoppingFlight:
    """A flight result from the shopping API."""

    price: float
    currency: str
    duration: int  # minutes
    stops: int
    legs: list["FlightLeg"]


@dataclass
class FlightLeg:
    """A single leg of a flight."""

    airline_code: str
    flight_number: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime
    duration: int  # minutes


# Mapping of currency codes to symbols
CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CNY": "¥",
    "TWD": "NT$",
    "KRW": "₩",
    "THB": "฿",
    "SGD": "S$",
    "HKD": "HK$",
    "AUD": "A$",
    "CAD": "C$",
}


def _extract_currency_from_token(token_b64: str) -> str | None:
    """Extract currency code from base64 booking token."""
    try:
        decoded = base64.b64decode(token_b64)
        match = re.search(rb"\x1a\x03([A-Z]{3})", decoded)
        if match:
            return match.group(1).decode("ascii")
    except Exception:
        pass
    return None


def _build_filters(
    from_airport: str,
    to_airport: str,
    date: str,
    return_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    infants_on_lap: int = 0,
    infants_in_seat: int = 0,
    seat_type: Literal["economy", "premium-economy", "business", "first"] = "economy",
    max_stops: int | None = None,
) -> list:
    """Build the filter structure for the shopping API."""
    # Trip type: 1 = one-way, 2 = round-trip
    trip_type = 2 if return_date else 1

    # Seat type mapping
    seat_map = {
        "economy": 1,
        "premium-economy": 2,
        "business": 3,
        "first": 4,
    }

    # Stops: 0 = any, 1 = nonstop, 2 = 1 stop, 3 = 2 stops
    stops_value = 0 if max_stops is None else min(max_stops + 1, 3)

    # Build flight segments
    segments = []

    # Outbound segment
    outbound = [
        [[[[from_airport, 0]]]],  # departure airport
        [[[[to_airport, 0]]]],  # arrival airport
        None,  # time restrictions
        stops_value,  # stops
        None,  # airlines
        None,  # placeholder
        date,  # travel date
        None,  # max duration
        None,  # selected flight
        None,  # layover airports
        None,
        None,
        None,  # layover duration
        None,  # emissions
        3,  # constant
    ]
    segments.append(outbound)

    # Return segment (if round-trip)
    if return_date:
        return_seg = [
            [[[[to_airport, 0]]]],
            [[[[from_airport, 0]]]],
            None,
            stops_value,
            None,
            None,
            return_date,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            3,
        ]
        segments.append(return_seg)

    filters = [
        [],
        [
            None,
            None,
            trip_type,
            None,
            [],
            seat_map[seat_type],
            [adults, children, infants_on_lap, infants_in_seat],
            None,  # price limit
            None,
            None,
            None,
            None,
            None,
            segments,
            None,
            None,
            None,
            1,
        ],
        0,  # sort_by
        0,
        0,
        2,
    ]

    return filters


def _encode_filters(filters: list) -> str:
    """URL-encode the filters for the API request."""
    json_str = json.dumps(filters, separators=(",", ":"))
    wrapped = [None, json_str]
    return urllib.parse.quote(json.dumps(wrapped, separators=(",", ":")))


def _parse_datetime(date_arr: list, time_arr: list) -> datetime:
    """Parse date and time arrays into datetime."""
    year = date_arr[0] or 2000
    month = date_arr[1] or 1
    day = date_arr[2] or 1
    hour = time_arr[0] if time_arr and len(time_arr) > 0 else 0
    minute = time_arr[1] if time_arr and len(time_arr) > 1 else 0
    return datetime(year, month, day, hour or 0, minute or 0)


def _parse_flight(data: list, currency: str) -> ShoppingFlight:
    """Parse a single flight from API response."""
    # Price
    price = 0.0
    try:
        if data[1] and data[1][0]:
            price = data[1][0][-1]
    except (IndexError, TypeError):
        pass

    # Duration and stops
    duration = data[0][9] if len(data[0]) > 9 else 0
    stops = len(data[0][2]) - 1 if len(data[0]) > 2 else 0

    # Parse legs
    legs = []
    for leg_data in data[0][2]:
        try:
            leg = FlightLeg(
                airline_code=leg_data[22][0] if len(leg_data) > 22 else "",
                flight_number=leg_data[22][1] if len(leg_data) > 22 else "",
                departure_airport=leg_data[3],
                arrival_airport=leg_data[6],
                departure_time=_parse_datetime(leg_data[20], leg_data[8]),
                arrival_time=_parse_datetime(leg_data[21], leg_data[10]),
                duration=leg_data[11],
            )
            legs.append(leg)
        except (IndexError, TypeError):
            continue

    return ShoppingFlight(
        price=price,
        currency=currency,
        duration=duration,
        stops=stops,
        legs=legs,
    )


def search_flights(
    from_airport: str,
    to_airport: str,
    date: str,
    return_date: str | None = None,
    *,
    adults: int = 1,
    children: int = 0,
    infants_on_lap: int = 0,
    infants_in_seat: int = 0,
    seat_type: Literal["economy", "premium-economy", "business", "first"] = "economy",
    max_stops: int | None = None,
    proxy: str | None = None,
) -> tuple[list[ShoppingFlight], str]:
    """Search for flights using the Shopping API.

    This is an alternative to the main get_flights() API that uses JSON
    encoding instead of Protobuf.

    Args:
        from_airport: Departure airport code (e.g., "TPE")
        to_airport: Arrival airport code (e.g., "NRT")
        date: Travel date in YYYY-MM-DD format
        return_date: Optional return date for round-trip
        adults: Number of adult passengers
        children: Number of children
        infants_on_lap: Number of infants on lap
        infants_in_seat: Number of infants in seat
        seat_type: Seat class
        max_stops: Maximum number of stops (None = any)
        proxy: Optional proxy URL

    Returns:
        Tuple of (list of flights, currency code)

    Example:
        >>> flights, currency = search_flights(
        ...     from_airport="TPE",
        ...     to_airport="NRT",
        ...     date="2026-05-01",
        ... )
        >>> for f in flights[:3]:
        ...     print(f"{f.price} {currency} - {f.stops} stops")
    """
    # Build and encode filters
    filters = _build_filters(
        from_airport=from_airport,
        to_airport=to_airport,
        date=date,
        return_date=return_date,
        adults=adults,
        children=children,
        infants_on_lap=infants_on_lap,
        infants_in_seat=infants_in_seat,
        seat_type=seat_type,
        max_stops=max_stops,
    )
    encoded = _encode_filters(filters)

    # Make request using curl_cffi if available (better browser impersonation)
    if HAS_CURL_CFFI:
        session = curl_requests.Session()
        response = session.post(
            url=SHOPPING_URL,
            data=f"f.req={encoded}",
            impersonate="chrome",
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
        )
        text = response.text
    else:
        # Fallback to primp
        client = Client(
            impersonate="chrome",
            impersonate_os="macos",
            referer=True,
            proxy=proxy,
            cookie_store=True,
        )
        response = client.post(
            url=SHOPPING_URL,
            content=f"f.req={encoded}".encode(),
            headers={
                "Cookie": CONSENT_COOKIE,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
        )
        text = response.text

    # Parse response
    # Response starts with )]}' for security
    text = text.lstrip(")]}'")

    try:
        outer = json.loads(text)
        inner_str = outer[0][2]
        if not inner_str:
            return [], "USD"

        data = json.loads(inner_str)
    except (json.JSONDecodeError, IndexError, TypeError):
        return [], "USD"

    # Extract flights from indices 2 and 3
    flights_data = []
    currency = "USD"

    for i in [2, 3]:
        if i < len(data) and isinstance(data[i], list) and data[i]:
            for item in data[i][0]:
                flights_data.append(item)
                # Try to extract currency from booking token
                if currency == "USD":
                    try:
                        if item[1] and len(item[1]) > 1 and isinstance(item[1][1], str):
                            detected = _extract_currency_from_token(item[1][1])
                            if detected:
                                currency = detected
                    except (IndexError, TypeError):
                        pass

    # Parse flights
    flights = [_parse_flight(f, currency) for f in flights_data]

    return flights, currency


def format_price(price: float, currency: str) -> str:
    """Format price with currency symbol."""
    symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    return f"{symbol}{price:,.0f}"
