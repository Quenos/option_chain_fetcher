"""
Export option chain data from SQLite database to JSON files.
One JSON file per expiration date, organized by strike with CALL/PUT sub-records.
"""
import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_fetch_timestamps(conn: sqlite3.Connection) -> List[str]:
    """Get all available fetch timestamps from the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT fetch_timestamp 
        FROM option_chain_data 
        ORDER BY fetch_timestamp DESC
    """)
    return [row[0] for row in cursor.fetchall()]


def get_expirations_for_fetch(
    conn: sqlite3.Connection,
    fetch_timestamp: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[str]:
    """Get all expiration dates for a specific fetch timestamp."""
    cursor = conn.cursor()
    
    query = """
        SELECT DISTINCT expiration_date 
        FROM option_chain_data 
        WHERE fetch_timestamp = ?
    """
    params: List[Any] = [fetch_timestamp]
    
    if start_date is not None:
        query += " AND expiration_date >= ?"
        params.append(start_date)
    
    if end_date is not None:
        query += " AND expiration_date <= ?"
        params.append(end_date)
    
    query += " ORDER BY expiration_date"
    
    cursor.execute(query, params)
    return [row[0] for row in cursor.fetchall()]


def get_option_data_for_expiration(
    conn: sqlite3.Connection,
    fetch_timestamp: str,
    expiration_date: str,
    min_strike: Optional[float] = None,
    max_strike: Optional[float] = None,
    min_delta: Optional[float] = None,
    max_delta: Optional[float] = None
) -> List[Dict[str, Any]]:
    """Get all option data for a specific expiration."""
    cursor = conn.cursor()
    
    # Build query with optional filters
    query = """
        SELECT 
            symbol, expiration_date, strike_price, option_type,
            bid_price, ask_price, mid_price,
            delta, gamma, theta, vega, rho,
            days_to_expiration
        FROM option_chain_data
        WHERE fetch_timestamp = ?
        AND expiration_date = ?
    """
    params: List[Any] = [fetch_timestamp, expiration_date]
    
    if min_strike is not None:
        query += " AND strike_price >= ?"
        params.append(min_strike)
    
    if max_strike is not None:
        query += " AND strike_price <= ?"
        params.append(max_strike)
    
    if min_delta is not None:
        query += " AND ABS(delta) >= ?"
        params.append(abs(min_delta))
    
    if max_delta is not None:
        query += " AND ABS(delta) <= ?"
        params.append(abs(max_delta))
    
    query += " ORDER BY strike_price, option_type"
    
    cursor.execute(query, params)
    
    columns = [desc[0] for desc in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    
    return results


def organize_data_by_strike(option_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Organize option data by strike price with CALL and PUT as sub-records.
    
    Returns:
        Dictionary with strikes as keys, each containing call and put data
    """
    strikes: Dict[float, Dict[str, Any]] = {}
    
    for option in option_data:
        strike = option['strike_price']
        option_type = option['option_type']
        
        if strike not in strikes:
            strikes[strike] = {
                'strike_price': strike,
                'call': None,
                'put': None
            }
        
        # Create option record without duplicating strike info
        option_record = {
            'symbol': option['symbol'],
            'bid_price': option['bid_price'],
            'ask_price': option['ask_price'],
            'mid_price': option['mid_price'],
            'delta': option['delta'],
            'gamma': option['gamma'],
            'theta': option['theta'],
            'vega': option['vega'],
            'rho': option['rho']
        }
        
        if option_type == 'CALL':
            strikes[strike]['call'] = option_record
        else:  # PUT
            strikes[strike]['put'] = option_record
    
    # Convert to sorted list
    sorted_strikes = sorted(strikes.items())
    return [strike_data for _, strike_data in sorted_strikes]


def get_underlying_price(
    conn: sqlite3.Connection,
    fetch_timestamp: str
) -> Dict[str, Optional[float]]:
    """Get the underlying price for a specific fetch timestamp."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, price, bid_price, ask_price
        FROM underlying_prices
        WHERE fetch_timestamp = ?
        LIMIT 1
    """, (fetch_timestamp,))
    
    row = cursor.fetchone()
    if row:
        return {
            'symbol': row[0],
            'price': row[1],
            'bid_price': row[2],
            'ask_price': row[3]
        }
    return {
        'symbol': None,
        'price': None,
        'bid_price': None,
        'ask_price': None
    }


def export_expiration_to_json(
    conn: sqlite3.Connection,
    fetch_timestamp: str,
    expiration_date: str,
    output_dir: Path,
    min_strike: Optional[float] = None,
    max_strike: Optional[float] = None,
    min_delta: Optional[float] = None,
    max_delta: Optional[float] = None
) -> str:
    """Export data for a single expiration to a JSON file."""
    
    # Get option data
    option_data = get_option_data_for_expiration(
        conn, fetch_timestamp, expiration_date,
        min_strike, max_strike, min_delta, max_delta
    )
    
    if not option_data:
        return None
    
    # Organize by strike
    strikes_data = organize_data_by_strike(option_data)
    
    # Get metadata
    days_to_expiration = option_data[0]['days_to_expiration']
    
    # Get underlying price
    underlying_data = get_underlying_price(conn, fetch_timestamp)
    
    # Create output structure
    output = {
        'metadata': {
            'fetch_timestamp': fetch_timestamp,
            'expiration_date': expiration_date,
            'days_to_expiration': days_to_expiration,
            'underlying_symbol': underlying_data['symbol'],
            'underlying_price': underlying_data['price'],
            'underlying_bid': underlying_data['bid_price'],
            'underlying_ask': underlying_data['ask_price'],
            'total_strikes': len(strikes_data),
            'strike_range': {
                'min': strikes_data[0]['strike_price'] if strikes_data else None,
                'max': strikes_data[-1]['strike_price'] if strikes_data else None
            },
            'export_timestamp': datetime.now().isoformat()
        },
        'strikes': strikes_data
    }
    
    # Create filename
    fetch_dt = datetime.fromisoformat(fetch_timestamp)
    filename = f"spx_options_{expiration_date}_{fetch_dt.strftime('%Y%m%d_%H%M%S')}.json"
    filepath = output_dir / filename
    
    # Write to file
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    return str(filepath)


def main() -> None:
    """Main function to export option chain data to JSON files."""
    parser = argparse.ArgumentParser(
        description='Export option chain data from SQLite to JSON files (one per expiration)'
    )
    parser.add_argument(
        '--db_path',
        type=str,
        default='database/option_chain_data.db',
        help='Path to SQLite database file (default: database/option_chain_data.db)'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default='json_exports',
        help='Output directory for JSON files (default: json_exports)'
    )
    parser.add_argument(
        '--fetch_timestamp',
        type=str,
        help='Specific fetch timestamp to export (default: latest)'
    )
    parser.add_argument(
        '--start_date',
        type=str,
        help='Start expiration date (YYYY-MM-DD format, inclusive)'
    )
    parser.add_argument(
        '--end_date',
        type=str,
        help='End expiration date (YYYY-MM-DD format, inclusive)'
    )
    parser.add_argument(
        '--min_strike',
        type=float,
        help='Minimum strike price to export'
    )
    parser.add_argument(
        '--max_strike',
        type=float,
        help='Maximum strike price to export'
    )
    parser.add_argument(
        '--min_delta',
        type=float,
        help='Minimum absolute delta to export (e.g., 0.20 for ±0.20)'
    )
    parser.add_argument(
        '--max_delta',
        type=float,
        help='Maximum absolute delta to export (e.g., 0.50 for ±0.50)'
    )
    parser.add_argument(
        '--expiration_date',
        type=str,
        help='Specific expiration date to export (YYYY-MM-DD format)'
    )
    
    args = parser.parse_args()
    
    print("===== SPX OPTION CHAIN JSON EXPORTER =====")
    print(f"Database: {args.db_path}")
    print(f"Output directory: {args.output_dir}")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Connect to database
        conn = sqlite3.connect(args.db_path)
        
        # Get fetch timestamp to use
        if args.fetch_timestamp:
            fetch_timestamp = args.fetch_timestamp
        else:
            timestamps = get_fetch_timestamps(conn)
            if not timestamps:
                print("No data found in database")
                return
            fetch_timestamp = timestamps[0]
            print(f"Using latest fetch: {fetch_timestamp}")
        
        # Display filter information
        if args.start_date or args.end_date:
            print(f"Expiration date range: {args.start_date or 'any'} to {args.end_date or 'any'}")
        if args.min_strike or args.max_strike:
            print(f"Strike range: {args.min_strike or 'any'} - {args.max_strike or 'any'}")
        if args.min_delta or args.max_delta:
            print(f"Delta range (absolute): {args.min_delta or 'any'} - {args.max_delta or 'any'}")
        
        # Get expirations to export
        if args.expiration_date:
            expirations = [args.expiration_date]
            print(f"Exporting single expiration: {args.expiration_date}")
        else:
            expirations = get_expirations_for_fetch(
                conn, fetch_timestamp, args.start_date, args.end_date
            )
            print(f"Found {len(expirations)} expirations to export")
        
        # Export each expiration
        exported_files = []
        for expiration in expirations:
            print(f"\nExporting {expiration}...", end=' ')
            filepath = export_expiration_to_json(
                conn,
                fetch_timestamp,
                expiration,
                output_dir,
                args.min_strike,
                args.max_strike,
                args.min_delta,
                args.max_delta
            )
            
            if filepath:
                exported_files.append(filepath)
                print(f"✓ {Path(filepath).name}")
            else:
                print("✗ No data")
        
        print(f"\n===== EXPORT COMPLETE =====")
        print(f"Exported {len(exported_files)} files to {output_dir}")
        
        if exported_files:
            print("\nExported files:")
            for filepath in exported_files:
                print(f"  - {Path(filepath).name}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
