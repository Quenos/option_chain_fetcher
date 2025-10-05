"""
Sample script to query option chain data from SQLite database.
"""
import argparse
import sqlite3
from datetime import datetime
from typing import List, Tuple


def get_latest_fetch_timestamp(conn: sqlite3.Connection) -> str:
    """Get the most recent fetch timestamp from the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(fetch_timestamp) FROM option_chain_data")
    result = cursor.fetchone()
    return result[0] if result[0] else ""


def get_all_fetch_timestamps(conn: sqlite3.Connection) -> List[str]:
    """Get all unique fetch timestamps."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT fetch_timestamp 
        FROM option_chain_data 
        ORDER BY fetch_timestamp DESC
    """)
    return [row[0] for row in cursor.fetchall()]


def query_by_delta(
    conn: sqlite3.Connection,
    fetch_timestamp: str,
    option_type: str,
    min_delta: float,
    max_delta: float
) -> List[Tuple]:
    """Query options by delta range."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            symbol, expiration_date, strike_price, 
            delta, bid_price, ask_price, mid_price,
            days_to_expiration
        FROM option_chain_data
        WHERE fetch_timestamp = ?
        AND option_type = ?
        AND delta BETWEEN ? AND ?
        ORDER BY expiration_date, strike_price
    """, (fetch_timestamp, option_type, min_delta, max_delta))
    return cursor.fetchall()


def query_by_expiration(
    conn: sqlite3.Connection,
    fetch_timestamp: str,
    expiration_date: str
) -> List[Tuple]:
    """Query all options for a specific expiration."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            symbol, option_type, strike_price, 
            delta, gamma, theta, vega, rho,
            bid_price, ask_price, mid_price
        FROM option_chain_data
        WHERE fetch_timestamp = ?
        AND expiration_date = ?
        ORDER BY option_type, strike_price
    """, (fetch_timestamp, expiration_date))
    return cursor.fetchall()


def get_summary_stats(conn: sqlite3.Connection, fetch_timestamp: str) -> dict:
    """Get summary statistics for a fetch."""
    cursor = conn.cursor()
    
    # Total options count
    cursor.execute("""
        SELECT COUNT(*) FROM option_chain_data 
        WHERE fetch_timestamp = ?
    """, (fetch_timestamp,))
    total_count = cursor.fetchone()[0]
    
    # Count by option type
    cursor.execute("""
        SELECT option_type, COUNT(*) 
        FROM option_chain_data 
        WHERE fetch_timestamp = ?
        GROUP BY option_type
    """, (fetch_timestamp,))
    type_counts = dict(cursor.fetchall())
    
    # Unique expirations
    cursor.execute("""
        SELECT COUNT(DISTINCT expiration_date) 
        FROM option_chain_data 
        WHERE fetch_timestamp = ?
    """, (fetch_timestamp,))
    expiration_count = cursor.fetchone()[0]
    
    # Strike range
    cursor.execute("""
        SELECT MIN(strike_price), MAX(strike_price) 
        FROM option_chain_data 
        WHERE fetch_timestamp = ?
    """, (fetch_timestamp,))
    min_strike, max_strike = cursor.fetchone()
    
    # DTE range
    cursor.execute("""
        SELECT MIN(days_to_expiration), MAX(days_to_expiration) 
        FROM option_chain_data 
        WHERE fetch_timestamp = ?
    """, (fetch_timestamp,))
    min_dte, max_dte = cursor.fetchone()
    
    return {
        'total_count': total_count,
        'type_counts': type_counts,
        'expiration_count': expiration_count,
        'strike_range': (min_strike, max_strike),
        'dte_range': (min_dte, max_dte)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Query option chain data')
    parser.add_argument(
        '--db_path',
        type=str,
        default='database/option_chain_data.db',
        help='Path to SQLite database file (default: database/option_chain_data.db)'
    )
    parser.add_argument(
        '--action',
        type=str,
        choices=['list', 'summary', 'delta', 'expiration'],
        default='summary',
        help='Action to perform'
    )
    parser.add_argument(
        '--fetch_timestamp',
        type=str,
        help='Specific fetch timestamp to query (default: latest)'
    )
    parser.add_argument(
        '--option_type',
        type=str,
        choices=['CALL', 'PUT'],
        help='Option type for delta query'
    )
    parser.add_argument(
        '--min_delta',
        type=float,
        help='Minimum delta for delta query'
    )
    parser.add_argument(
        '--max_delta',
        type=float,
        help='Maximum delta for delta query'
    )
    parser.add_argument(
        '--expiration_date',
        type=str,
        help='Expiration date (YYYY-MM-DD) for expiration query'
    )
    
    args = parser.parse_args()
    
    try:
        conn = sqlite3.connect(args.db_path)
        
        if args.action == 'list':
            # List all fetch timestamps
            timestamps = get_all_fetch_timestamps(conn)
            print(f"Found {len(timestamps)} fetch timestamps:")
            for ts in timestamps:
                dt = datetime.fromisoformat(ts)
                print(f"  {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        else:
            # Get fetch timestamp to use
            if args.fetch_timestamp:
                fetch_timestamp = args.fetch_timestamp
            else:
                fetch_timestamp = get_latest_fetch_timestamp(conn)
                if not fetch_timestamp:
                    print("No data found in database")
                    return
                print(f"Using latest fetch: {fetch_timestamp}\n")
            
            if args.action == 'summary':
                stats = get_summary_stats(conn, fetch_timestamp)
                print("=== Summary Statistics ===")
                print(f"Total Options: {stats['total_count']}")
                print(f"  CALLs: {stats['type_counts'].get('CALL', 0)}")
                print(f"  PUTs: {stats['type_counts'].get('PUT', 0)}")
                print(f"Unique Expirations: {stats['expiration_count']}")
                print(f"Strike Range: {stats['strike_range'][0]:.2f} - {stats['strike_range'][1]:.2f}")
                print(f"DTE Range: {stats['dte_range'][0]} - {stats['dte_range'][1]} days")
            
            elif args.action == 'delta':
                if not all([args.option_type, args.min_delta is not None, args.max_delta is not None]):
                    print("Error: --option_type, --min_delta, and --max_delta are required for delta query")
                    return
                
                results = query_by_delta(
                    conn, fetch_timestamp, args.option_type,
                    args.min_delta, args.max_delta
                )
                
                print(f"=== {args.option_type}s with delta between {args.min_delta} and {args.max_delta} ===")
                print(f"Found {len(results)} options:\n")
                print(f"{'Symbol':<20} {'Exp Date':<12} {'Strike':>8} {'Delta':>8} {'Bid':>8} {'Ask':>8} {'Mid':>8} {'DTE':>5}")
                print("-" * 100)
                
                for row in results:
                    symbol, exp_date, strike, delta, bid, ask, mid, dte = row
                    print(f"{symbol:<20} {exp_date:<12} {strike:>8.2f} {delta:>8.4f} {bid:>8.2f} {ask:>8.2f} {mid:>8.2f} {dte:>5}")
            
            elif args.action == 'expiration':
                if not args.expiration_date:
                    print("Error: --expiration_date is required for expiration query")
                    return
                
                results = query_by_expiration(conn, fetch_timestamp, args.expiration_date)
                
                print(f"=== Options expiring on {args.expiration_date} ===")
                print(f"Found {len(results)} options:\n")
                print(f"{'Symbol':<20} {'Type':<5} {'Strike':>8} {'Delta':>8} {'Gamma':>8} {'Theta':>8} {'Bid':>8} {'Ask':>8} {'Mid':>8}")
                print("-" * 120)
                
                for row in results:
                    symbol, opt_type, strike, delta, gamma, theta, vega, rho, bid, ask, mid = row
                    print(f"{symbol:<20} {opt_type:<5} {strike:>8.2f} {delta:>8.4f} {gamma:>8.4f} {theta:>8.4f} {bid:>8.2f} {ask:>8.2f} {mid:>8.2f}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
