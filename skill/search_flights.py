#!/usr/bin/env python3
"""Search flights using Google Flights API."""

import argparse
import json
import sys


def format_datetime(dt):
    """Format SimpleDatetime object."""
    if not dt:
        return None
    try:
        date_str = f"{dt.date[0]}-{dt.date[1]:02d}-{dt.date[2]:02d}"
        if dt.time and len(dt.time) >= 2:
            time_str = f"{dt.time[0]:02d}:{dt.time[1]:02d}"
            return f"{date_str} {time_str}"
        return date_str
    except:
        return str(dt)


def format_duration(minutes):
    """Format duration in minutes to human readable."""
    if not minutes:
        return None
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"


def search_flights(args):
    """Search for flights."""
    try:
        from fast_flights import get_flights, create_query, FlightQuery, Passengers
        
        # Build flight queries
        flight_queries = [
            FlightQuery(
                date=args.departure,
                from_airport=args.from_airport,
                to_airport=args.to_airport,
            )
        ]
        
        # Add return flight if specified
        if args.return_date:
            flight_queries.append(
                FlightQuery(
                    date=args.return_date,
                    from_airport=args.to_airport,
                    to_airport=args.from_airport,
                )
            )
        
        # Create query
        query = create_query(
            flights=flight_queries,
            seat="economy",
            trip="round-trip" if args.return_date else "one-way",
            passengers=Passengers(adults=args.adults, children=args.children),
        )
        
        # Get flights (returns MetaList of Flights objects)
        flights = get_flights(query)
        
        # Format results
        results = []
        cheapest = None
        
        for flight_group in flights:
            # Each flight_group is a Flights object with multiple legs
            legs = []
            total_duration = 0
            
            for leg in flight_group.flights:
                leg_data = {
                    "from": leg.from_airport.code if leg.from_airport else None,
                    "to": leg.to_airport.code if leg.to_airport else None,
                    "departure": format_datetime(leg.departure),
                    "arrival": format_datetime(leg.arrival),
                    "duration": format_duration(leg.duration),
                    "plane": leg.plane_type if hasattr(leg, 'plane_type') else None,
                }
                legs.append(leg_data)
                total_duration += leg.duration if leg.duration else 0
            
            flight_data = {
                "airlines": flight_group.airlines if hasattr(flight_group, 'airlines') else [],
                "price": float(flight_group.price) if hasattr(flight_group, 'price') else None,
                "currency": args.currency,
                "total_duration": format_duration(total_duration),
                "stops": len(flight_group.flights) - 1 if flight_group.flights else 0,
                "legs": legs,
                "type": flight_group.type if hasattr(flight_group, 'type') else None,
            }
            results.append(flight_data)
            
            # Track cheapest
            price = flight_data["price"]
            if price and (cheapest is None or price < cheapest):
                cheapest = price
        
        output = {
            "success": True,
            "query": {
                "from": args.from_airport,
                "to": args.to_airport,
                "departure": args.departure,
                "return": args.return_date,
                "adults": args.adults,
                "children": args.children,
                "currency": args.currency,
            },
            "flights": results,
            "total": len(results),
            "cheapest": {
                "price": cheapest,
                "currency": args.currency,
            } if cheapest else None,
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
                "departure": args.departure,
            }
        }
        print(json.dumps(error_output, indent=2, ensure_ascii=False), file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Search flights using Google Flights")
    
    # Required arguments
    parser.add_argument("--from", dest="from_airport", required=True,
                        help="Departure airport code (e.g., FRA)")
    parser.add_argument("--to", dest="to_airport", required=True,
                        help="Arrival airport code (e.g., PEK)")
    parser.add_argument("--departure", required=True,
                        help="Departure date (YYYY-MM-DD)")
    
    # Optional arguments
    parser.add_argument("--return", dest="return_date",
                        help="Return date (YYYY-MM-DD) for round trip")
    parser.add_argument("--adults", type=int, default=1,
                        help="Number of adults (default: 1)")
    parser.add_argument("--children", type=int, default=0,
                        help="Number of children (default: 0)")
    parser.add_argument("--currency", default="EUR",
                        help="Currency code (default: EUR)")
    
    args = parser.parse_args()
    return search_flights(args)


if __name__ == "__main__":
    sys.exit(main())
