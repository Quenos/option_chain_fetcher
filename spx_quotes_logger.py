import logging
import time
from configparser import ConfigParser
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import pandas_market_calendars as mcal
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient
from pytz import timezone
from tastytrade.instruments import NestedOptionChain
from tastytrade.utils import now_in_new_york

from market_data import MarketData
from session import ApplicationSession

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler("spx_quotes.log", maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SPXQuotesLogger")

# Suppress logs from external packages
for name in [
    "tastytrade", "tastytrade.instruments", "tastytrade.streamer", "tastytrade.utils",
    "pymongo", "urllib3", "requests", "asyncio"
]:
    logging.getLogger(name).setLevel(logging.WARNING)

# Global Mongo client and config loading
def load_config():
    config = ConfigParser()
    if not config.read('config.ini'):
        raise FileNotFoundError("Could not read config.ini")
    return config

CONFIG = load_config()
MONGO_CLIENT = MongoClient(
    f"mongodb://{CONFIG['MONGODB']['User']}:{CONFIG['MONGODB']['Password']}@{CONFIG['MONGODB']['URI']}:27017",
    serverSelectionTimeoutMS=5000
)
MONGO_CLIENT.server_info()
DB = MONGO_CLIENT[CONFIG['MONGODB']['DB_NAME'].strip("[]'\"")]

def get_mongo_collection(collection_key):
    name = CONFIG['MONGODB'][collection_key].strip("[]'\"")
    return DB[name]

def get_spx_price(market_data):
    time.sleep(3)
    market_data.subscribe_quotes(["SPX"])

    for attempt in range(10):
        time.sleep(2)
        prices = market_data.get_quotes(["SPX"])
        logger.info(f"Attempt {attempt + 1}: Retrieved {len(prices)} SPX quotes")
        if prices:
            price = prices[0]
            ask = getattr(price, 'ask_price', 0) or 0
            bid = getattr(price, 'bid_price', 0) or 0
            if ask and bid:
                mid = (ask + bid) / 2
                logger.info(f"SPX mid price: {mid}")
                return mid
            elif ask or bid:
                val = ask or bid
                logger.info(f"SPX price (single side): {val}")
                return val
    logger.error("Could not get valid SPX price after all attempts")
    raise RuntimeError("Could not fetch SPX price.")

def get_option_symbols_around_spx(spx_price):
    session = ApplicationSession().session
    chains = NestedOptionChain.get(session, 'SPX')
    today = now_in_new_york().date()
    nearest_expiry = next(
        (exp for chain in chains for exp in chain.expirations if exp.expiration_date >= today),
        None
    )
    if not nearest_expiry:
        raise RuntimeError("No valid SPX expiry found.")
    min_strike = float(spx_price) * 0.98
    max_strike = float(spx_price) * 1.02
    symbols = []
    for strike in nearest_expiry.strikes:
        strike_price = strike.strike_price
        if min_strike <= strike_price <= max_strike:
            if hasattr(strike, 'call_streamer_symbol') and hasattr(strike, 'put_streamer_symbol'):
                if strike_price < spx_price:
                    symbols.append(strike.put_streamer_symbol)
                if strike_price > spx_price:
                    symbols.append(strike.call_streamer_symbol)
    return symbols, nearest_expiry.expiration_date

def store_option_quotes(symbols, expiry, market_data):
    logger.info("[store_option_quotes] Collecting quotes...")
    logger.info(f"[store_option_quotes] Subscribing to {symbols}")
    market_data.subscribe_quotes(symbols)
    time.sleep(10)
    quotes = market_data.get_quotes(symbols)
    logger.info(f"[store_option_quotes] Retrieved {len(quotes)} quotes")
    market_data.subscribe_greeks(symbols)
    time.sleep(2)
    greeks_list = market_data.get_greeks(symbols)
    greeks_map = {g.event_symbol: g for g in greeks_list} if greeks_list else {}
    logger.info(f"[store_option_quotes] Retrieved {len(greeks_map)} greeks")
    ts = now_in_new_york()
    records = []
    for q in quotes:
        symbol = getattr(q, 'event_symbol', None)
        greeks = greeks_map.get(symbol)
        bid = float(getattr(q, 'bid_price', -1))
        ask = float(getattr(q, 'ask_price', -1))
        delta = float(getattr(greeks, 'delta', -1)) if greeks else -1
        iv = float(getattr(greeks, 'volatility', -1)) if greeks else -1
        if bid == -1 or ask == -1 or delta == -1 or iv == -1:
            continue
        records.append({
            'symbol': symbol,
            'bid': bid,
            'ask': ask,
            'timestamp': ts,
            'expiry': expiry.strftime('%Y-%m-%d'),
            'delta': delta,
            'iv': iv,
        })
    logger.info(f"[store_option_quotes] Retrieved {len(records)} records")
    if records:
        collection = get_mongo_collection('SPX_OPTION_QUOTES_COLLECTION')
        collection.insert_many(records)
        logger.info(f"[store_option_quotes] Inserted {len(records)} quotes at {ts.strftime('%H:%M:%S')} EST.")
    else:
        logger.warning("[store_option_quotes] No quotes to insert.")

def store_spx_price(market_data):
    price = get_spx_price(market_data)
    ts = now_in_new_york()
    collection = get_mongo_collection('SPX_PRICE_COLLECTION')
    collection.insert_one({'price': float(price), 'timestamp': ts})
    logger.info(f"[store_spx_price] Inserted SPX price at {ts.strftime('%H:%M:%S')} EST.")

def shutdown(scheduler):
    logger.info("[Shutdown] Stopping scheduler at %s", time.strftime('%Y-%m-%d %H:%M:%S'))
    scheduler.shutdown(wait=False)

def is_market_open_today():
    nyse = mcal.get_calendar('NYSE')
    today = datetime.now(timezone('US/Eastern')).date()
    schedule = nyse.schedule(start_date=str(today), end_date=str(today))
    return not schedule.empty

def main():
    if not is_market_open_today():
        logger.info("Market is closed today. Exiting.")
        return

    market_data = MarketData()
    market_data.start_streamer()

    spx_price = get_spx_price(market_data)
    logger.info(f"SPX price at 9:35am EST: {spx_price}")
    symbols, expiry = get_option_symbols_around_spx(spx_price)
    logger.info(f"Tracking {len(symbols)} option symbols for expiry {expiry}")

    eastern = timezone('US/Eastern')
    scheduler = BackgroundScheduler(timezone=eastern)

    nyse = mcal.get_calendar('NYSE')
    today = datetime.now(eastern).date()
    market_schedule = nyse.schedule(start_date=str(today), end_date=str(today))
    market_close_time = market_schedule.iloc[0]['market_close'] if not market_schedule.empty else None
    shutdown_time = market_close_time + timedelta(minutes=5) if market_close_time else None

    try:
        # Schedule jobs
        scheduler.add_job(store_option_quotes, 'cron', hour=9, minute='40,50', second=0,
                          args=[symbols, expiry, market_data])
        scheduler.add_job(store_option_quotes, 'cron', hour='10-15', minute='*/10', second=0,
                          args=[symbols, expiry, market_data])
        scheduler.add_job(store_option_quotes, 'cron', hour=16, minute=0, second=0,
                          args=[symbols, expiry, market_data])

        scheduler.add_job(store_spx_price, 'cron', hour=9, minute='30-59', second=0,
                          args=[market_data])
        scheduler.add_job(store_spx_price, 'cron', hour='10-15', minute='*', second=0,
                          args=[market_data])
        scheduler.add_job(store_spx_price, 'cron', hour=16, minute=0, second=0,
                          args=[market_data])

        if shutdown_time:
            scheduler.add_job(shutdown, 'date', run_date=shutdown_time, args=[scheduler])

        scheduler.start()

        while scheduler.running:
            time.sleep(1)

    except (KeyboardInterrupt, SystemExit) as e:
        logger.info("[Main] Exit requested: %s", e)

    finally:
        market_data.stop_streamer()
        logger.info("[Main] Stopped market data streamer. Script complete.")

if __name__ == "__main__":
    main()
