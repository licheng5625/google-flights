#!/usr/bin/env python3
"""Get price calendar graph (fixed duration) using Google Flights API."""

import argparse
import json
import sys


def calendar_graph(args):
    """Get price calendar graph for fixed trip duration."""
    try:
        from fast_flights import get_calendar_graph
        
        # Build search parameters
        params = {
            "from_airport": args.from_airport,
            "to_airport": args.to_airport,
            "date_range": tuple(args.date_range),
            "trip_duration": args.duration,
            "adults": args.adults,
            "currency": args.currency,
        }
        
        if args.children:
            params["children"] = args.children
        
        if args.seat_class:
            params["seat_class"] = args.seat_class
        
        if args.max_stops is not None:
            params["max_stops"] = args.max_stops
        
        if args.max_duration:
            params["max_duration"] = args.max_duration
        
        if args.separate_tickets:
            params["separate_tickets"] = True
        
        # Get calendar
        calendar = get_calendar_graph(**params)
        
        # Format results
        entries = []
        for entry in calendar.entries:
            entries.append({
                "outbound_date": entry.outbound_date,
                "return_date": entry.return_date,
                "price": entry.price,
                "currency": entry.currency,
            })
        
        # Find cheapest
        cheapest = calendar.cheapest()
        most_expensive = calendar.most_expensive()
        
        output = {
            "success": True,
            "query": {
                "from": args.from_airport,
                "to": args.to_airport,
                "date_range": args.date_range,
                "trip_duration": args.duration,
                "adults": args.adults,
                "currency": args.currency,
            },
            "entries": entries,
            "total": len(entries),
            "cheapest": {
                "outbound_date": cheapest.outbound_date,
                "return_date": cheapest.return_date,
                "price": cheapest.price,
                "currency": cheapest.currency,
            } if cheapest else None,
            "most_expensive": {
                "outbound_date": most_expensive.outbound_date,
                "return_date": most_expensive.return_date,
                "price": most_expensive.price,
                "currency": most_expensive.currency,
            } if most_expensive else None,
        }
        
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
        
    except Exception as e:
        error_output = {
            "success": False,
            "error": str(e),
            "query": {
                "from": args.from_airport,
                "to": args.to_airport,
                "date_range": args.date_range,
                "duration": args.duration,
            }
        }
        print(json.dumps(error_output, indent=2, ensure_ascii=False), file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Get price calendar graph for fixed trip duration")
    
    # Required arguments
    parser.add_argument("--from", dest="from_airport", required=True,
                        help="Departure airport code (e.g., FRA)")
    parser.add_argument("--to", dest="to_airport", required=True,
                        help="Arrival airport code (e.g., TAO)")
    parser.add_argument("--date-range", nargs=2, required=True,
                        metavar=("START", "END"),
                        help="Date range for departures (YYYY-MM-DD YYYY-MM-DD)")
    parser.add_argument("--duration", type=int, required=True,
                        help="Fixed trip duration in days")
    
    # Optional arguments
    parser.add_argument("--adults", type=int, default=1,
                        help="Number of adults (default: 1)")
    parser.add_argument("--children", type=int, default=0,
                        help="Number of children (default: 0)")
    parser.add_argument("--seat-class", type=int, choices=[1, 2, 3, 4],
                        help="1=economy, 2=premium, 3=business, 4=first")
    parser.add_argument("--max-stops", type=int, choices=[0, 1, 2],
                        help="0=nonstop, 1=1 stop, 2=2+ stops")
    parser.add_argument("--max-duration", type=int,
                        help="Max flight duration in minutes")
    parser.add_argument("--separate-tickets", action="store_true",
                        help="Allow separate tickets")
    parser.add_argument("--currency", default="EUR",
                        help="Currency code (default: EUR)")
    
    args = parser.parse_args()
    return calendar_graph(args)


if __name__ == "__main__":
    sys.exit(main())
