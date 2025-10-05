# SPX/SPXW Symbol Handling

## Overview
The option chain fetcher has been enhanced to automatically handle the peculiarity of SPX options, which come in two variants:

- **SPX**: Monthly and quarterly expirations (typically 3rd Friday of the month)
- **SPXW**: Weekly expirations (Monday, Wednesday, Friday)

## Automatic Dual Fetching

When you specify either `--symbol SPX` or `--symbol SPXW`, the script automatically fetches **BOTH** symbol types. This ensures complete market coverage without requiring multiple script runs.

### Implementation Details

```python
# In get_option_chains() function:
if symbol.upper() in ['SPX', 'SPXW']:
    symbols_to_fetch = ['SPX', 'SPXW']
else:
    symbols_to_fetch = [symbol]
```

- **Case-insensitive**: Works with 'SPX', 'spx', 'SPXW', 'spxw'
- **Independent error handling**: If one symbol fails, the other continues
- **Combined results**: All options stored in single database with same fetch_timestamp

## Why This Matters

Without this feature, you would need to:
1. Run the script with `--symbol SPX` to get monthly options
2. Run the script again with `--symbol SPXW` to get weekly options
3. Manually combine the results

Now you just run once and get everything.

## Examples

### Fetch All SPX Options (0-7 DTE)
```bash
python option_chain_fetcher.py \
    --max_dte 7 \
    --min_strike 5800 \
    --max_strike 6000 \
    --symbol SPX
```

This single command fetches:
- All SPX monthly/quarterly expirations within 7 days
- All SPXW weekly expirations within 7 days
- Complete Greeks and quotes for both

### Query Results by Symbol Type

```python
import sqlite3

conn = sqlite3.connect('option_chain_data.db')
cursor = conn.cursor()

# Get only SPXW (weekly) options
cursor.execute("""
    SELECT symbol, expiration_date, strike_price, delta
    FROM option_chain_data
    WHERE symbol LIKE 'SPXW%'
    AND option_type = 'CALL'
    ORDER BY expiration_date, strike_price
""")

# Get only SPX (monthly/quarterly) options
cursor.execute("""
    SELECT symbol, expiration_date, strike_price, delta
    FROM option_chain_data
    WHERE symbol LIKE 'SPX%'
    AND symbol NOT LIKE 'SPXW%'
    AND option_type = 'CALL'
    ORDER BY expiration_date, strike_price
""")

conn.close()
```

## Symbol Identification

In the database, you can identify which type each option is:
- **SPX monthly**: `SPX250117C5900` (no 'W' after SPX)
- **SPXW weekly**: `SPXW250110C5900` (has 'W' after SPX)

## Logging

The script logs when it detects SPX/SPXW and provides clear feedback:

```
INFO - Fetching option chains for SPX
INFO - Parameters: max_dte=7, min_strike=5800.0, max_strike=6000.0
INFO - Fetching both SPX (monthly/quarterly) and SPXW (weekly) option chains
INFO - Fetching option chains for SPX
INFO - Fetching option chains for SPXW
INFO - Found 245 options to fetch data for
```

## Error Handling

If one symbol type fails (e.g., API issue with SPXW), the other continues:

```python
for fetch_symbol in symbols_to_fetch:
    try:
        option_chains = NestedOptionChain.get(session, fetch_symbol)
    except Exception as e:
        logger.error(f"Error fetching option chains for {fetch_symbol}: {str(e)}")
        continue  # Continue with next symbol
```

This ensures partial data collection even if one symbol type has issues.

## Underlying Price Tracking

### SPX Price for Both Symbol Types

When fetching SPX or SPXW options, the script automatically fetches the **SPX** underlying price (not SPXW), since both option types reference the same underlying index.

**Important**: The underlying price is stored in the `underlying_prices` table with the symbol `SPX`, regardless of whether you specified `--symbol SPX` or `--symbol SPXW`.

### Implementation

```python
# Always use SPX for the underlying, not SPXW
underlying_symbol = 'SPX' if symbol.upper() in ['SPX', 'SPXW'] else symbol
```

This ensures:
- Single price point for both SPX and SPXW options
- Accurate representation since SPXW options are priced off the SPX index
- Consistency across fetches

### Database Storage

The `underlying_prices` table stores:
- `symbol`: Always 'SPX' for SPX/SPXW options
- `price`: Mid price (calculated from bid/ask)
- `bid_price`: Bid price
- `ask_price`: Ask price
- `fetch_timestamp`: Links to the option data

### JSON Export

The underlying price is automatically included in the metadata of exported JSON files:

```json
{
  "metadata": {
    "fetch_timestamp": "2025-10-05T16:48:23.456789",
    "underlying_symbol": "SPX",
    "underlying_price": 5923.50,
    "underlying_bid": 5923.25,
    "underlying_ask": 5923.75,
    ...
  }
}
```

## Other Symbols

For symbols other than SPX/SPXW (e.g., SPY, QQQ), the script fetches:
- That single symbol's option chain
- That symbol's underlying price (e.g., SPY underlying for SPY options)
