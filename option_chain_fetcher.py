import argparse
import logging
import sqlite3
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tastytrade.instruments import NestedOptionChain

from market_data import MarketData
from session import ApplicationSession

# Remove existing log file before starting
LOG_FILE = "option_chain_fetcher.log"
if Path(LOG_FILE).exists():
    Path(LOG_FILE).unlink()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("OptionChainFetcher")

# Suppress tastytrade package logging if local logger is active
if logger.hasHandlers():
    for name in ["tastytrade", "tastytrade.instruments", "tastytrade.streamer", "tastytrade.utils"]:
        logging.getLogger(name).setLevel(logging.INFO)

POLL_INTERVAL = 5


def init_database(db_path: str) -> sqlite3.Connection:
    """
    Initialize SQLite database and create tables if they don't exist.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        sqlite3.Connection: Database connection object
    """
    logger.info(f"Initializing database at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table for option chain data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS option_chain_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            expiration_date TEXT NOT NULL,
            strike_price REAL NOT NULL,
            option_type TEXT NOT NULL,
            bid_price REAL,
            ask_price REAL,
            mid_price REAL,
            delta REAL,
            gamma REAL,
            theta REAL,
            vega REAL,
            rho REAL,
            days_to_expiration INTEGER NOT NULL,
            UNIQUE(fetch_timestamp, symbol)
        )
    """)
    
    # Create table for underlying prices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS underlying_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL,
            bid_price REAL,
            ask_price REAL,
            UNIQUE(fetch_timestamp, symbol)
        )
    """)
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fetch_timestamp 
        ON option_chain_data(fetch_timestamp)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_expiration_date 
        ON option_chain_data(expiration_date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_underlying_fetch_timestamp 
        ON underlying_prices(fetch_timestamp)
    """)
    
    conn.commit()
    logger.info("Database initialized successfully")
    return conn


def get_option_chains(
    session: Any,
    symbol: str,
    max_dte: int,
    min_strike: float,
    max_strike: float
) -> List[Dict[str, Any]]:
    """
    Fetch option chains for specified symbol within DTE and strike range.
    
    Note: For SPX, this fetches both SPX (monthly/quarterly) and SPXW (weekly) chains.
    
    Args:
        session: TastyTrade session object
        symbol: Underlying symbol (e.g., 'SPX' or 'SPXW')
        max_dte: Maximum days to expiration
        min_strike: Minimum strike price
        max_strike: Maximum strike price
        
    Returns:
        List of dictionaries containing option chain information
    """
    logger.info(f"Fetching option chains for {symbol}")
    logger.info(f"Parameters: max_dte={max_dte}, min_strike={min_strike}, max_strike={max_strike}")
    
    # Handle SPX/SPXW: fetch both monthly and weekly chains
    symbols_to_fetch = []
    if symbol.upper() in ['SPX', 'SPXW']:
        symbols_to_fetch = ['SPX', 'SPXW']
        logger.info("Fetching both SPX (monthly/quarterly) and SPXW (weekly) option chains")
    else:
        symbols_to_fetch = [symbol]
    
    today = date.today()
    options_list: List[Dict[str, Any]] = []
    
    # Fetch chains for each symbol
    for fetch_symbol in symbols_to_fetch:
        logger.info(f"Fetching option chains for {fetch_symbol}")
        try:
            option_chains = NestedOptionChain.get(session, fetch_symbol)
        except Exception as e:
            logger.error(f"Error fetching option chains for {fetch_symbol}: {str(e)}")
            continue
        
        _process_option_chains(option_chains, today, max_dte, min_strike, max_strike, options_list)
    
    logger.info(f"Found {len(options_list)} options to fetch data for")
    return options_list


def _process_option_chains(
    option_chains: Any,
    today: date,
    max_dte: int,
    min_strike: float,
    max_strike: float,
    options_list: List[Dict[str, Any]]
) -> None:
    """
    Process option chains and add to options_list.
    
    Args:
        option_chains: Option chain data from TastyTrade
        today: Current date
        max_dte: Maximum days to expiration
        min_strike: Minimum strike price
        max_strike: Maximum strike price
        options_list: List to append option data to (modified in place)
    """
    
    for option_chain in option_chains:
        for expiration in option_chain.expirations:
            exp_date = expiration.expiration_date
            days_to_expiration = (exp_date - today).days
            
            # Filter by DTE
            if days_to_expiration < 0 or days_to_expiration > max_dte:
                logger.debug(f"Skipping expiration {exp_date} (DTE: {days_to_expiration})")
                continue
            
            logger.info(f"Processing expiration {exp_date} (DTE: {days_to_expiration})")
            
            for strike in expiration.strikes:
                strike_price = float(strike.strike_price)  # Convert Decimal to float for SQLite
                
                # Filter by strike range
                if strike_price < min_strike or strike_price > max_strike:
                    continue
                
                # Add CALL option
                if hasattr(strike, 'call_streamer_symbol') and strike.call_streamer_symbol:
                    options_list.append({
                        'symbol': strike.call_streamer_symbol,
                        'expiration_date': exp_date.isoformat(),
                        'strike_price': strike_price,
                        'option_type': 'CALL',
                        'days_to_expiration': days_to_expiration
                    })
                
                # Add PUT option
                if hasattr(strike, 'put_streamer_symbol') and strike.put_streamer_symbol:
                    options_list.append({
                        'symbol': strike.put_streamer_symbol,
                        'expiration_date': exp_date.isoformat(),
                        'strike_price': strike_price,
                        'option_type': 'PUT',
                        'days_to_expiration': days_to_expiration
                    })


def fetch_quotes(
    market_data: MarketData,
    symbols: List[str]
) -> Dict[str, Tuple[Optional[float], Optional[float], Optional[float]]]:
    """
    Fetch bid, ask, and mid prices for given symbols.
    
    Args:
        market_data: MarketData instance
        symbols: List of option symbols
        
    Returns:
        Dictionary mapping symbol to (bid, ask, mid) tuple
    """
    logger.info(f"Fetching quotes for {len(symbols)} symbols")
    market_data.subscribe_quotes(symbols)
    
    quotes_map: Dict[str, Tuple[Optional[float], Optional[float], Optional[float]]] = {}
    symbols_left = set(symbols)
    max_attempts = 50
    
    for attempt in range(max_attempts):
        fresh_quotes = market_data.get_quotes(list(symbols_left))
        
        for quote in fresh_quotes:
            bid = quote.bid_price if hasattr(quote, 'bid_price') else None
            ask = quote.ask_price if hasattr(quote, 'ask_price') else None
            mid = (bid + ask) / 2 if bid is not None and ask is not None else None
            
            quotes_map[quote.event_symbol] = (bid, ask, mid)
            if quote.event_symbol in symbols_left:
                symbols_left.remove(quote.event_symbol)
        
        if not symbols_left:
            logger.info(f"Successfully fetched quotes for all {len(symbols)} symbols")
            break
        
        logger.debug(f"Attempt {attempt + 1}/{max_attempts}: {len(symbols_left)} symbols remaining")
        time.sleep(POLL_INTERVAL)
    
    if symbols_left:
        logger.warning(f"Failed to fetch quotes for {len(symbols_left)} symbols: {list(symbols_left)[:10]}")
    
    return quotes_map


def fetch_greeks(
    market_data: MarketData,
    symbols: List[str]
) -> Dict[str, Dict[str, Optional[float]]]:
    """
    Fetch Greeks (delta, gamma, theta, vega, rho) for given symbols.
    
    Args:
        market_data: MarketData instance
        symbols: List of option symbols
        
    Returns:
        Dictionary mapping symbol to dictionary of greeks
    """
    logger.info(f"Fetching Greeks for {len(symbols)} symbols")
    market_data.subscribe_greeks(symbols)
    
    greeks_map: Dict[str, Dict[str, Optional[float]]] = {}
    symbols_left = set(symbols)
    max_attempts = 50
    
    for attempt in range(max_attempts):
        fresh_greeks = market_data.get_greeks(list(symbols_left))
        
        for greek in fresh_greeks:
            greeks_data = {
                'delta': greek.delta if hasattr(greek, 'delta') else None,
                'gamma': greek.gamma if hasattr(greek, 'gamma') else None,
                'theta': greek.theta if hasattr(greek, 'theta') else None,
                'vega': greek.vega if hasattr(greek, 'vega') else None,
                'rho': greek.rho if hasattr(greek, 'rho') else None
            }
            
            greeks_map[greek.event_symbol] = greeks_data
            if greek.event_symbol in symbols_left:
                symbols_left.remove(greek.event_symbol)
        
        if not symbols_left:
            logger.info(f"Successfully fetched Greeks for all {len(symbols)} symbols")
            break
        
        logger.debug(f"Attempt {attempt + 1}/{max_attempts}: {len(symbols_left)} symbols remaining")
        time.sleep(POLL_INTERVAL)
    
    if symbols_left:
        logger.warning(f"Failed to fetch Greeks for {len(symbols_left)} symbols: {list(symbols_left)[:10]}")
    
    return greeks_map


def fetch_underlying_price(
    market_data: MarketData,
    symbol: str
) -> Tuple[str, Optional[float], Optional[float], Optional[float]]:
    """
    Fetch the current price of the underlying symbol.
    For SPX/SPXW, always fetches SPX (not SPXW) for the underlying.
    
    Args:
        market_data: MarketData instance
        symbol: Underlying symbol from command line (e.g., SPX, SPXW, AAPL)
        
    Returns:
        Tuple of (underlying_symbol, mid_price, bid_price, ask_price)
    """
    # For SPX/SPXW options, always use SPX for the underlying, not SPXW
    underlying_symbol = 'SPX' if symbol.upper() in ['SPX', 'SPXW'] else symbol
    
    logger.info(f"Fetching underlying price for {underlying_symbol}")
    market_data.subscribe_quotes([underlying_symbol])
    
    max_attempts = 50
    
    for attempt in range(max_attempts):
        quotes = market_data.get_quotes([underlying_symbol])
        
        if quotes:
            quote = quotes[0]
            bid = quote.bid_price if hasattr(quote, 'bid_price') else None
            ask = quote.ask_price if hasattr(quote, 'ask_price') else None
            mid = (bid + ask) / 2 if bid is not None and ask is not None else None
            
            logger.info(f"Successfully fetched {underlying_symbol} price: {mid} (bid: {bid}, ask: {ask})")
            return (underlying_symbol, mid, bid, ask)
        
        logger.debug(f"Attempt {attempt + 1}/{max_attempts}: waiting for {underlying_symbol} quote")
        time.sleep(POLL_INTERVAL)
    
    logger.warning(f"Failed to fetch underlying price for {underlying_symbol}")
    return (underlying_symbol, None, None, None)


def store_underlying_price(
    conn: sqlite3.Connection,
    fetch_timestamp: str,
    symbol: str,
    price: Optional[float],
    bid_price: Optional[float],
    ask_price: Optional[float]
) -> None:
    """
    Store underlying price data in SQLite database.
    
    Args:
        conn: Database connection
        fetch_timestamp: Timestamp when data was fetched
        symbol: Underlying symbol (e.g., 'SPX')
        price: Mid price of the underlying
        bid_price: Bid price of the underlying
        ask_price: Ask price of the underlying
    """
    logger.info(f"Storing underlying price for {symbol}")
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO underlying_prices (
                fetch_timestamp, symbol, price, bid_price, ask_price
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            fetch_timestamp,
            symbol,
            float(price) if price is not None else None,
            float(bid_price) if bid_price is not None else None,
            float(ask_price) if ask_price is not None else None
        ))
        conn.commit()
        logger.info(f"Successfully stored underlying price for {symbol}: {price}")
    except Exception as e:
        logger.error(f"Error storing underlying price for {symbol}: {str(e)}")


def store_option_data(
    conn: sqlite3.Connection,
    fetch_timestamp: str,
    options_list: List[Dict[str, Any]],
    quotes_map: Dict[str, Tuple[Optional[float], Optional[float], Optional[float]]],
    greeks_map: Dict[str, Dict[str, Optional[float]]]
) -> None:
    """
    Store option chain data in SQLite database.
    
    Args:
        conn: Database connection
        fetch_timestamp: Timestamp when data was fetched
        options_list: List of option information
        quotes_map: Dictionary of quotes data
        greeks_map: Dictionary of Greeks data
    """
    logger.info(f"Storing data for {len(options_list)} options")
    cursor = conn.cursor()
    
    stored_count = 0
    for option in options_list:
        symbol = option['symbol']
        
        # Get quotes data
        bid, ask, mid = quotes_map.get(symbol, (None, None, None))
        
        # Get Greeks data
        greeks = greeks_map.get(symbol, {})
        delta = greeks.get('delta')
        gamma = greeks.get('gamma')
        theta = greeks.get('theta')
        vega = greeks.get('vega')
        rho = greeks.get('rho')
        
        try:
            # Convert all numeric values to float to avoid Decimal issues with SQLite
            cursor.execute("""
                INSERT OR REPLACE INTO option_chain_data (
                    fetch_timestamp, symbol, expiration_date, strike_price,
                    option_type, bid_price, ask_price, mid_price,
                    delta, gamma, theta, vega, rho, days_to_expiration
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fetch_timestamp,
                symbol,
                option['expiration_date'],
                float(option['strike_price']),
                option['option_type'],
                float(bid) if bid is not None else None,
                float(ask) if ask is not None else None,
                float(mid) if mid is not None else None,
                float(delta) if delta is not None else None,
                float(gamma) if gamma is not None else None,
                float(theta) if theta is not None else None,
                float(vega) if vega is not None else None,
                float(rho) if rho is not None else None,
                option['days_to_expiration']
            ))
            stored_count += 1
        except Exception as e:
            logger.error(f"Error storing data for {symbol}: {str(e)}")
    
    conn.commit()
    logger.info(f"Successfully stored {stored_count} option records")


def clear_database(db_path: str) -> None:
    """
    Clear all data from the database tables.
    
    Args:
        db_path: Path to the SQLite database file
    """
    logger.info(f"Clearing database at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM option_chain_data")
        deleted_options = cursor.rowcount
        logger.info(f"Deleted {deleted_options} records from option_chain_data")
        
        cursor.execute("DELETE FROM underlying_prices")
        deleted_underlying = cursor.rowcount
        logger.info(f"Deleted {deleted_underlying} records from underlying_prices")
        
        conn.commit()
        logger.info("Database cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing database: {str(e)}")
        raise
    finally:
        conn.close()


def main() -> None:
    """
    Main function to fetch and store option chain data.
    """
    parser = argparse.ArgumentParser(
        description='Fetch SPX option chain data including Greeks and quotes'
    )
    parser.add_argument(
        '--max_dte',
        type=int,
        help='Maximum days to expiration'
    )
    parser.add_argument(
        '--min_strike',
        type=float,
        help='Minimum strike price'
    )
    parser.add_argument(
        '--max_strike',
        type=float,
        help='Maximum strike price'
    )
    parser.add_argument(
        '--symbol',
        type=str,
        default='SPX',
        help='Underlying symbol (default: SPX)'
    )
    parser.add_argument(
        '--db_path',
        type=str,
        default='database/option_chain_data.db',
        help='Path to SQLite database file (default: database/option_chain_data.db)'
    )
    parser.add_argument(
        '--clear_db',
        action='store_true',
        help='Clear all data from the database and exit'
    )
    
    args = parser.parse_args()
    
    # Handle database clear operation
    if args.clear_db:
        logger.info("===== CLEARING DATABASE =====")
        from pathlib import Path
        db_path = Path(args.db_path)
        if not db_path.exists():
            logger.warning(f"Database file does not exist: {args.db_path}")
            return
        clear_database(args.db_path)
        logger.info("===== DATABASE CLEARED =====")
        return
    
    # Validate required arguments for data fetching
    if args.max_dte is None or args.min_strike is None or args.max_strike is None:
        parser.error("--max_dte, --min_strike, and --max_strike are required unless using --clear_db")
    
    logger.info("===== STARTING OPTION CHAIN DATA FETCHER =====")
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Max DTE: {args.max_dte}")
    logger.info(f"Strike Range: {args.min_strike} - {args.max_strike}")
    logger.info(f"Database: {args.db_path}")
    
    # Record fetch timestamp
    fetch_timestamp = datetime.now().isoformat()
    logger.info(f"Fetch timestamp: {fetch_timestamp}")
    
    try:
        # Create database directory if it doesn't exist
        from pathlib import Path
        db_path = Path(args.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        conn = init_database(args.db_path)
        
        # Initialize session and market data
        logger.info("Initializing TastyTrade session")
        session = ApplicationSession().session
        
        logger.info("Initializing market data streamer")
        market_data = MarketData()
        market_data.start_streamer()
        
        # Give streamer time to initialize
        time.sleep(2)
        
        # Get option chains
        options_list = get_option_chains(
            session,
            args.symbol,
            args.max_dte,
            args.min_strike,
            args.max_strike
        )
        
        if not options_list:
            logger.warning("No options found matching the criteria")
            return
        
        # Extract symbols for data fetching
        symbols = [opt['symbol'] for opt in options_list]
        
        # Fetch underlying price (for SPX/SPXW, fetches SPX; for others, fetches the actual symbol)
        underlying_symbol, underlying_price, underlying_bid, underlying_ask = fetch_underlying_price(
            market_data,
            args.symbol
        )
        
        # Store underlying price
        store_underlying_price(
            conn,
            fetch_timestamp,
            underlying_symbol,
            underlying_price,
            underlying_bid,
            underlying_ask
        )
        
        # Fetch quotes
        quotes_map = fetch_quotes(market_data, symbols)
        
        # Fetch Greeks
        greeks_map = fetch_greeks(market_data, symbols)
        
        # Store data in database
        store_option_data(
            conn,
            fetch_timestamp,
            options_list,
            quotes_map,
            greeks_map
        )
        
        logger.info("===== DATA FETCH COMPLETED SUCCESSFULLY =====")
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}", exc_info=True)
        raise
    finally:
        # Clean up
        if 'conn' in locals():
            conn.close()
            logger.info("Database connection closed")
        if 'market_data' in locals():
            market_data.stop_streamer()
            logger.info("Market data streamer stopped")


if __name__ == "__main__":
    main()