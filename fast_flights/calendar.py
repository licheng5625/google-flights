"""Google Flights Calendar APIs - Get price grid/graph for date ranges.

Uses curl_cffi for browser impersonation, which allows requests without
additional authentication tokens.
"""

import json
import urllib.parse
from dataclasses import dataclass, field

from curl_cffi import requests

CALENDAR_GRID_URL = "https://www.google.com/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/GetCalendarGrid"
CALENDAR_PICKER_URL = "https://www.google.com/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/GetCalendarPicker"


@dataclass
class CalendarEntry:
    """A single entry in the price calendar grid."""

    outbound_date: str
    return_date: str
    price: float
    currency: str = "USD"


@dataclass
class PriceCalendar:
    """Price calendar/grid result."""

    entries: list[CalendarEntry] = field(default_factory=list)
    currency: str = "USD"

    def cheapest(self) -> CalendarEntry | None:
        """Get the cheapest entry."""
        if not self.entries:
            return None
        return min(self.entries, key=lambda e: e.price)

    def most_expensive(self) -> CalendarEntry | None:
        """Get the most expensive entry."""
        if not self.entries:
            return None
        return max(self.entries, key=lambda e: e.price)

    def by_outbound_date(self, date: str) -> list[CalendarEntry]:
        """Get all entries for a specific outbound date."""
        return [e for e in self.entries if e.outbound_date == date]

    def by_return_date(self, date: str) -> list[CalendarEntry]:
        """Get all entries for a specific return date."""
        return [e for e in self.entries if e.return_date == date]


# Location type constants
AIRPORT = 0
CITY = 4


def _build_request_data(
    src_location: tuple[str, int],
    dst_location: tuple[str, int],
    departure_start: str,
    departure_end: str,
    return_start: str,
    return_end: str,
    outbound_date: str,
    return_date: str,
    adults: int = 1,
    children: int = 0,
    infants_on_lap: int = 0,
    infants_in_seat: int = 0,
    seat_class: int = 1,
    stops: int = 0,
    trip_type: int = 1,
    outbound_times: tuple[int, int, int, int] | None = None,
    return_times: tuple[int, int, int, int] | None = None,
    max_duration: int | None = None,
    bags: tuple[int, int] | None = None,
    separate_tickets: bool = False,
) -> str:
    """Build the f.req parameter for GetCalendarGrid.

    Args:
        src_location: (code, type) tuple. Type: 0=airport, 4=city MID
        dst_location: (code, type) tuple
        departure_start: Start of departure date range (YYYY-MM-DD)
        departure_end: End of departure date range (YYYY-MM-DD)
        return_start: Start of return date range (YYYY-MM-DD)
        return_end: End of return date range (YYYY-MM-DD)
        outbound_date: Reference outbound date (YYYY-MM-DD)
        return_date: Reference return date (YYYY-MM-DD)
        adults: Number of adults
        children: Number of children
        infants_on_lap: Number of infants on lap
        infants_in_seat: Number of infants in seat
        seat_class: 1=economy, 2=premium, 3=business, 4=first
        stops: 0=any, 1=nonstop, 2=1 stop, 3=2+ stops
        trip_type: 1=round-trip, 2=one-way
        outbound_times: (earliest_dep, latest_dep, earliest_arr, latest_arr) in hours (0-24)
        return_times: (earliest_dep, latest_dep, earliest_arr, latest_arr) in hours (0-24)
        max_duration: Maximum flight duration in minutes
        bags: (checked_bags, carry_on) - number of bags required
        separate_tickets: Allow separate tickets for outbound/return

    Returns:
        URL-encoded request data string
    """
    # Format time restrictions
    outbound_time_filter = list(outbound_times) if outbound_times else None
    return_time_filter = list(return_times) if return_times else None

    # Format duration filter
    duration_filter = [max_duration] if max_duration else None

    # Format bags filter
    bags_filter = list(bags) if bags else None

    # separate_tickets flag: 1 to enable, None to disable
    separate_tickets_flag = 1 if separate_tickets else None

    # Build inner data structure matching Google Flights API format
    inner_data = [
        None,
        [
            None, None, trip_type, None, [], seat_class,
            [adults, children, infants_on_lap, infants_in_seat],
            None, None, None,
            bags_filter,  # index 10: baggage requirements
            None, None,
            [
                # Outbound segment
                [
                    [[[src_location[0], src_location[1]]]],
                    [[[dst_location[0], dst_location[1]]]],
                    outbound_time_filter, stops, None, None,
                    outbound_date,
                    duration_filter, None, None, None, None, None, None, 3
                ],
                # Return segment
                [
                    [[[dst_location[0], dst_location[1]]]],
                    [[[src_location[0], src_location[1]]]],
                    return_time_filter, stops, None, None,
                    return_date,
                    duration_filter, None, None, None, None, None, None, 3
                ]
            ],
            None, None, None, 1,
            separate_tickets_flag,  # index 18: separate tickets flag
            None, None, None, None,
            [dst_location[0]]
        ],
        [departure_start, departure_end],
        [return_start, return_end]
    ]

    inner_json = json.dumps(inner_data, separators=(',', ':'))
    outer = [None, inner_json]
    outer_json = json.dumps(outer, separators=(',', ':'))

    return urllib.parse.quote(outer_json)


def _parse_response(text: str, currency: str) -> list[CalendarEntry]:
    """Parse the calendar grid response."""
    entries = []

    if text.startswith(")]}'"):
        text = text[4:]

    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if line.isdigit() or not line.startswith('['):
            continue

        try:
            data = json.loads(line)
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], list) and data[0][0] == "wrb.fr":
                    if len(data[0]) > 2 and data[0][2]:
                        inner = json.loads(data[0][2])
                        if isinstance(inner, list) and len(inner) > 1 and isinstance(inner[1], list):
                            for offer in inner[1]:
                                if isinstance(offer, list) and len(offer) >= 3:
                                    date1 = offer[0]
                                    date2 = offer[1]
                                    price_data = offer[2]
                                    if isinstance(price_data, list) and len(price_data) >= 1:
                                        if isinstance(price_data[0], list) and len(price_data[0]) >= 2:
                                            price = price_data[0][1]
                                            if price and price > 0:
                                                entries.append(CalendarEntry(
                                                    outbound_date=date1,
                                                    return_date=date2 or "",
                                                    price=float(price),
                                                    currency=currency
                                                ))
        except json.JSONDecodeError:
            continue

    return entries


def get_calendar_grid(
    from_airport: str | None = None,
    to_airport: str | None = None,
    from_city: str | None = None,
    to_city: str | None = None,
    departure_range: tuple[str, str] = ("", ""),
    return_range: tuple[str, str] = ("", ""),
    *,
    outbound_date: str | None = None,
    return_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    infants_on_lap: int = 0,
    infants_in_seat: int = 0,
    seat_class: int = 1,
    max_stops: int | None = None,
    max_duration: int | None = None,
    bags: tuple[int, int] | None = None,
    outbound_times: tuple[int, int, int, int] | None = None,
    return_times: tuple[int, int, int, int] | None = None,
    separate_tickets: bool = False,
    currency: str = "USD",
    language: str = "en",
) -> PriceCalendar:
    """Get price calendar/grid for date ranges.

    Returns a 2D grid of prices for all combinations of departure and return
    dates within the specified ranges.

    Args:
        from_airport: Departure airport code (e.g., "TPE")
        to_airport: Arrival airport code (e.g., "NRT")
        from_city: Departure city MID (e.g., "/m/02z0j" for Shanghai)
        to_city: Arrival city MID (e.g., "/m/01l3s0" for Beijing)
        departure_range: (start_date, end_date) for departure dates
        return_range: (start_date, end_date) for return dates
        outbound_date: Reference outbound date (defaults to departure_range[0])
        return_date: Reference return date (defaults to return_range[0])
        adults: Number of adults
        children: Number of children
        infants_on_lap: Number of infants on lap
        infants_in_seat: Number of infants in seat
        seat_class: 1=economy, 2=premium, 3=business, 4=first
        max_stops: Max stops (None=any, 0=nonstop, 1=1 stop, 2=2+ stops)
        max_duration: Maximum flight duration in minutes (e.g., 1080 = 18 hours)
        bags: (checked_bags, carry_on) - number of bags required
        outbound_times: (earliest_dep, latest_dep, earliest_arr, latest_arr) in hours 0-24
        return_times: (earliest_dep, latest_dep, earliest_arr, latest_arr) in hours 0-24
        separate_tickets: Allow separate tickets (分段机票) - may find cheaper options
        currency: Currency code
        language: Language code

    Returns:
        PriceCalendar with price entries for all date combinations

    Example:
        >>> from fast_flights import get_calendar_grid
        >>> calendar = get_calendar_grid(
        ...     from_airport="FRA",
        ...     to_airport="TAO",
        ...     departure_range=("2026-04-28", "2026-05-05"),
        ...     return_range=("2026-05-20", "2026-05-31"),
        ...     max_stops=1,
        ...     max_duration=1080,  # 18 hours max
        ...     bags=(1, 0),  # require checked bag
        ... )
        >>> cheapest = calendar.cheapest()
    """
    # Determine source location
    if from_airport:
        src_location = (from_airport, AIRPORT)
    elif from_city:
        src_location = (from_city, CITY)
    else:
        raise ValueError("Either from_airport or from_city must be specified")

    # Determine destination location
    if to_airport:
        dst_location = (to_airport, AIRPORT)
    elif to_city:
        dst_location = (to_city, CITY)
    else:
        raise ValueError("Either to_airport or to_city must be specified")

    # Default reference dates to range starts
    if not outbound_date:
        outbound_date = departure_range[0]
    if not return_date:
        return_date = return_range[0]

    # Stops mapping: 0=any, 1=nonstop, 2=1stop, 3=2+stops
    # User passes max_stops: None=any, 0=nonstop, 1=1stop, 2=2+stops
    if max_stops is None:
        stops_val = 0
    else:
        stops_val = max_stops + 1

    # Build request
    encoded = _build_request_data(
        src_location=src_location,
        dst_location=dst_location,
        departure_start=departure_range[0],
        departure_end=departure_range[1],
        return_start=return_range[0],
        return_end=return_range[1],
        outbound_date=outbound_date,
        return_date=return_date,
        adults=adults,
        children=children,
        infants_on_lap=infants_on_lap,
        infants_in_seat=infants_in_seat,
        seat_class=seat_class,
        stops=stops_val,
        outbound_times=outbound_times,
        return_times=return_times,
        max_duration=max_duration,
        bags=bags,
        separate_tickets=separate_tickets,
    )

    # Build URL
    url = (
        f"{CALENDAR_GRID_URL}?"
        f"f.sid=5718184525488592449&"
        f"bl=boq_travel-frontend-flights-ui_20260303.06_p0&"
        f"hl={language}&"
        f"gl=US&"
        f"curr={currency}&"
        f"soc-app=162&soc-platform=1&soc-device=1&"
        f"_reqid=983392&rt=c"
    )

    # Create client with browser impersonation
    client = requests.Session()
    client.headers.update({
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
    })

    # Make request
    response = client.post(
        url=url,
        data=f"f.req={encoded}",
        impersonate="chrome",
        allow_redirects=True,
    )

    if response.status_code != 200:
        raise Exception(f"Calendar grid request failed with status {response.status_code}")

    entries = _parse_response(response.text, currency)

    return PriceCalendar(entries=entries, currency=currency)


def _build_graph_request_data(
    src_location: tuple[str, int],
    dst_location: tuple[str, int],
    date_range_start: str,
    date_range_end: str,
    outbound_date: str,
    return_date: str,
    trip_duration: int,
    adults: int = 1,
    children: int = 0,
    infants_on_lap: int = 0,
    infants_in_seat: int = 0,
    seat_class: int = 1,
    stops: int = 0,
    max_duration: int | None = None,
    bags: tuple[int, int] | None = None,
    outbound_times: tuple[int, int, int, int] | None = None,
    return_times: tuple[int, int, int, int] | None = None,
    separate_tickets: bool = False,
) -> str:
    """Build the f.req parameter for GetCalendarPicker (graph mode).

    Args:
        src_location: (code, type) tuple
        dst_location: (code, type) tuple
        date_range_start: Start of date range (YYYY-MM-DD)
        date_range_end: End of date range (YYYY-MM-DD)
        outbound_date: Reference outbound date (YYYY-MM-DD)
        return_date: Reference return date (YYYY-MM-DD)
        trip_duration: Fixed trip duration in days
        adults: Number of adults
        seat_class: 1=economy, 2=premium, 3=business, 4=first
        stops: 0=any, 1=nonstop, 2=1 stop, 3=2+ stops
        max_duration: Maximum flight duration in minutes
        bags: (checked_bags, carry_on) - number of bags required
        outbound_times: (earliest_dep, latest_dep, earliest_arr, latest_arr) in hours (0-24)
        return_times: (earliest_dep, latest_dep, earliest_arr, latest_arr) in hours (0-24)
        separate_tickets: Allow separate tickets for outbound/return

    Returns:
        URL-encoded request data string
    """
    # Format time restrictions
    outbound_time_filter = list(outbound_times) if outbound_times else None
    return_time_filter = list(return_times) if return_times else None

    # Format duration filter
    duration_filter = [max_duration] if max_duration else None

    # Format bags filter
    bags_filter = list(bags) if bags else None

    # separate_tickets flag: 1 to enable, None to disable
    separate_tickets_flag = 1 if separate_tickets else None

    # Build inner data structure for GetCalendarPicker
    inner_data = [
        None,
        [
            None, None, 1, None, [], seat_class,  # trip_type=1 (round-trip)
            [adults, children, infants_on_lap, infants_in_seat],
            None, None, None,
            bags_filter,  # index 10: baggage requirements
            None, None,
            [
                # Outbound segment
                [
                    [[[src_location[0], src_location[1]]]],
                    [[[dst_location[0], dst_location[1]]]],
                    outbound_time_filter, stops, None, None,
                    outbound_date,
                    duration_filter, None, None, None, None, None, None, 3
                ],
                # Return segment
                [
                    [[[dst_location[0], dst_location[1]]]],
                    [[[src_location[0], src_location[1]]]],
                    return_time_filter, stops, None, None,
                    return_date,
                    duration_filter, None, None, None, None, None, None, 3
                ]
            ],
            None, None, None, 1,
            separate_tickets_flag,  # index 18: separate tickets flag
            None, None, None, None,
            [dst_location[0]]
        ],
        [date_range_start, date_range_end],
        None,  # no return range (using fixed duration)
        [trip_duration, trip_duration]  # trip duration range
    ]

    inner_json = json.dumps(inner_data, separators=(',', ':'))
    outer = [None, inner_json]
    outer_json = json.dumps(outer, separators=(',', ':'))

    return urllib.parse.quote(outer_json)


def get_calendar_graph(
    from_airport: str | None = None,
    to_airport: str | None = None,
    from_city: str | None = None,
    to_city: str | None = None,
    date_range: tuple[str, str] = ("", ""),
    trip_duration: int = 7,
    *,
    outbound_date: str | None = None,
    return_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    infants_on_lap: int = 0,
    infants_in_seat: int = 0,
    seat_class: int = 1,
    max_stops: int | None = None,
    max_duration: int | None = None,
    bags: tuple[int, int] | None = None,
    outbound_times: tuple[int, int, int, int] | None = None,
    return_times: tuple[int, int, int, int] | None = None,
    separate_tickets: bool = False,
    currency: str = "USD",
    language: str = "en",
) -> PriceCalendar:
    """Get price calendar/graph for a date range with fixed trip duration.

    Unlike get_calendar_grid which returns a 2D matrix of all departure/return
    combinations, this returns a 1D list of prices for departures within the
    date range, with a fixed return duration.

    Args:
        from_airport: Departure airport code (e.g., "FRA")
        to_airport: Arrival airport code (e.g., "TAO")
        from_city: Departure city MID (e.g., "/m/02z0j" for Shanghai)
        to_city: Arrival city MID (e.g., "/m/01l3s0" for Beijing)
        date_range: (start_date, end_date) for departure dates
        trip_duration: Fixed trip duration in days (e.g., 14 for 2 weeks)
        outbound_date: Reference outbound date (defaults to date_range[0])
        return_date: Reference return date (auto-calculated from duration)
        adults: Number of adults
        seat_class: 1=economy, 2=premium, 3=business, 4=first
        max_stops: Max stops (None=any, 0=nonstop, 1=1 stop, 2=2+ stops)
        max_duration: Maximum flight duration in minutes (e.g., 1080 = 18 hours)
        bags: (checked_bags, carry_on) - number of bags required
        outbound_times: (earliest_dep, latest_dep, earliest_arr, latest_arr) in hours 0-24
        return_times: (earliest_dep, latest_dep, earliest_arr, latest_arr) in hours 0-24
        separate_tickets: Allow separate tickets (分段机票) - may find cheaper options
        currency: Currency code
        language: Language code

    Returns:
        PriceCalendar with price entries

    Example:
        >>> from fast_flights import get_calendar_graph
        >>> # Find cheapest 2-week trip in May-June, allowing separate tickets
        >>> calendar = get_calendar_graph(
        ...     from_airport="FRA",
        ...     to_airport="TAO",
        ...     date_range=("2026-05-01", "2026-06-30"),
        ...     trip_duration=14,
        ...     max_stops=1,
        ...     max_duration=1080,  # 18 hours max
        ...     outbound_times=(6, 22, 0, 24),  # depart 6am-10pm
        ...     separate_tickets=True,  # 分段机票
        ... )
        >>> cheapest = calendar.cheapest()
    """
    # Determine source location
    if from_airport:
        src_location = (from_airport, AIRPORT)
    elif from_city:
        src_location = (from_city, CITY)
    else:
        raise ValueError("Either from_airport or from_city must be specified")

    # Determine destination location
    if to_airport:
        dst_location = (to_airport, AIRPORT)
    elif to_city:
        dst_location = (to_city, CITY)
    else:
        raise ValueError("Either to_airport or to_city must be specified")

    # Default reference dates
    if not outbound_date:
        outbound_date = date_range[0]
    if not return_date:
        # Calculate return date from outbound + duration
        from datetime import datetime, timedelta
        out_dt = datetime.strptime(outbound_date, "%Y-%m-%d")
        ret_dt = out_dt + timedelta(days=trip_duration)
        return_date = ret_dt.strftime("%Y-%m-%d")

    # Stops mapping
    if max_stops is None:
        stops_val = 0
    else:
        stops_val = max_stops + 1

    # Build request
    encoded = _build_graph_request_data(
        src_location=src_location,
        dst_location=dst_location,
        date_range_start=date_range[0],
        date_range_end=date_range[1],
        outbound_date=outbound_date,
        return_date=return_date,
        trip_duration=trip_duration,
        adults=adults,
        children=children,
        infants_on_lap=infants_on_lap,
        infants_in_seat=infants_in_seat,
        seat_class=seat_class,
        stops=stops_val,
        max_duration=max_duration,
        bags=bags,
        outbound_times=outbound_times,
        return_times=return_times,
        separate_tickets=separate_tickets,
    )

    # Build URL
    url = (
        f"{CALENDAR_PICKER_URL}?"
        f"f.sid=5718184525488592449&"
        f"bl=boq_travel-frontend-flights-ui_20260303.06_p0&"
        f"hl={language}&"
        f"gl=US&"
        f"curr={currency}&"
        f"soc-app=162&soc-platform=1&soc-device=1&"
        f"_reqid=983392&rt=c"
    )

    # Create client with browser impersonation
    client = requests.Session()
    client.headers.update({
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
    })

    # Make request
    response = client.post(
        url=url,
        data=f"f.req={encoded}",
        impersonate="chrome",
        allow_redirects=True,
    )

    if response.status_code != 200:
        raise Exception(f"Calendar graph request failed with status {response.status_code}")

    entries = _parse_response(response.text, currency)

    return PriceCalendar(entries=entries, currency=currency)


# Alias for backwards compatibility
get_price_calendar = get_calendar_grid
