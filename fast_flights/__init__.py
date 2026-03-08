from . import integrations

from .querying import (
    FlightQuery,
    Query,
    Passengers,
    create_query,
    create_query as create_filter,  # alias
)
from .fetcher import get_flights, fetch_flights_html
from .calendar import (
    get_price_calendar,
    get_calendar_grid,
    get_calendar_graph,
    PriceCalendar,
    CalendarEntry,
    AIRPORT,
    CITY,
)

__all__ = [
    # Main API (Protobuf-based)
    "FlightQuery",
    "Query",
    "Passengers",
    "create_query",
    "create_filter",
    "get_flights",
    "fetch_flights_html",
    # Calendar API
    "get_price_calendar",
    "get_calendar_grid",
    "get_calendar_graph",
    "PriceCalendar",
    "CalendarEntry",
    "AIRPORT",
    "CITY",
    # Integrations
    "integrations",
]
