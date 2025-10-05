import numpy as np
import pandas as pd

from spx_quotes_logger import calculate_ivr_from_prices


def test_calculate_ivr_from_prices_flat():
    prices = pd.Series([100.0] * 365)
    ivr = calculate_ivr_from_prices(prices)
    print(f"Flat prices IVR: {ivr}")
    assert ivr == 0.0

def test_calculate_ivr_from_prices_high_vol_end():
    # Low volatility for most of the year, high volatility at the end
    np.random.seed(0)
    base = np.ones(365) * 100
    # Add small noise for most of the year
    base[:335] += np.random.normal(0, 0.5, 335)
    # Add high noise at the end
    base[335:] += np.random.normal(0, 10, 30)
    prices = pd.Series(base)
    ivr = calculate_ivr_from_prices(prices)
    print(f"High volatility at end IVR: {ivr}")
    assert 80 <= ivr <= 100

def test_calculate_ivr_from_prices_known():
    base = np.ones(365) * 100
    base[180:210] += np.linspace(0, 50, 30)  # spike
    prices = pd.Series(base)
    ivr = calculate_ivr_from_prices(prices)
    print(f"Spike scenario IVR: {ivr}")
    assert 0 <= ivr <= 100 