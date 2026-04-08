"""
Instrument Scanner for Systematic Futures Trading
Finds the best instruments that pass Carver's granularity test at $1M capital
"""

import logging
logging.basicConfig(level=logging.WARNING)

from systems.provided.futures_chapter15.basesystem import futures_system
from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
import pandas as pd

# Get all available instruments
data = csvFuturesSimData()
all_instruments = data.get_instrument_list()

print(f"Scanning {len(all_instruments)} instruments...")
print("=" * 80)

# Configuration for scanning
CAPITAL = 1_000_000  # $1M
VOL_TARGET = 0.15    # 15% annual volatility target
MIN_POSITION = 4     # Carver's granularity threshold

results = []

for inst in all_instruments:
    try:
        # Create single-instrument system
        config = Config()
        config.trading_rules = {
            "ewmac16_64": {
                "function": "systems.provided.rules.ewmac.ewmac_forecast_with_defaults",
                "data": ["rawdata.daily_prices", "rawdata.daily_returns_volatility"],
                "other_args": {"Lfast": 16, "Lslow": 64}
            },
            "carry": {
                "function": "systems.provided.rules.carry.carry_forecast_with_defaults",
                "data": ["rawdata.raw_carry"]
            }
        }
        
        config.instrument_weights = {inst: 1.0}
        config.instrument_div_multiplier = 1.0
        config.forecast_weights = {"ewmac16_64": 0.5, "carry": 0.5}
        config.forecast_div_multiplier = 1.0
        config.percentage_vol_target = VOL_TARGET * 100
        config.notional_trading_capital = CAPITAL
        
        system = futures_system(config=config)
        
        # Get max position (at forecast=20)
        positions = system.portfolio.get_notional_position(inst)
        max_position = positions.abs().max()
        
        # Get Sharpe ratio
        account = system.accounts.pandl_for_instrument(inst)
        sharpe = account.sharpe()
        
        # Get data range
        prices = data.get_backadjusted_futures_price(inst)
        years = len(prices) / 252
        
        # Categorize asset class (rough heuristic)
        if any(x in inst for x in ['US', 'BUND', 'GILT', 'JGB', 'OAT', 'BTP', 'BOBL']):
            asset_class = 'Bonds'
        elif any(x in inst for x in ['SP', 'NASDAQ', 'DOW', 'FTSE', 'DAX', 'CAC', 'NIKKEI', 'HANG', 'EUROSTX', 'RUSSELL', 'KOSPI']):
            asset_class = 'Equities'
        elif any(x in inst for x in ['CRUDE', 'BRENT', 'GAS', 'HEAT', 'GASOI']):
            asset_class = 'Energy'
        elif any(x in inst for x in ['GOLD', 'SILVER', 'COPPER', 'PLAT', 'PALLAD']):
            asset_class = 'Metals'
        elif any(x in inst for x in ['CORN', 'WHEAT', 'SOYBEAN', 'SUGAR', 'COFFEE', 'COTTON', 'COCOA', 'RICE']):
            asset_class = 'Ags'
        elif any(x in inst for x in ['EUR', 'GBP', 'JPY', 'AUD', 'CHF', 'CAD', 'MXP', 'NZD']):
            asset_class = 'FX'
        elif any(x in inst for x in ['VIX', 'V2X']):
            asset_class = 'Vol'
        elif any(x in inst for x in ['BITCOIN', 'ETHEREUM']):
            asset_class = 'Crypto'
        else:
            asset_class = 'Other'
        
        # Store results
        results.append({
            'Instrument': inst,
            'Asset Class': asset_class,
            'Max Position': max_position,
            'Sharpe': sharpe,
            'Years': years,
            'Pass Granularity': 'YES' if max_position >= MIN_POSITION else 'NO'
        })
        
        print(f"{inst:>15} | {asset_class:>10} | Max Pos: {max_position:>6.1f} | SR: {sharpe:>5.2f} | {years:>4.1f}y | {'PASS' if max_position >= MIN_POSITION else 'FAIL'}")
        
    except Exception as e:
        print(f"{inst:>15} | ERROR: {str(e)[:50]}")
        continue

# Convert to DataFrame and analyze
df = pd.DataFrame(results)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Filter instruments that pass granularity test
passed = df[df['Pass Granularity'] == 'YES'].copy()
passed = passed.sort_values('Sharpe', ascending=False)

print(f"\nTotal instruments scanned: {len(df)}")
print(f"Passed granularity test (max pos ≥ {MIN_POSITION}): {len(passed)}")
print(f"Failed granularity test: {len(df) - len(passed)}")

print("\n" + "=" * 80)
print("TOP 20 INSTRUMENTS BY SHARPE RATIO (that pass granularity)")
print("=" * 80)
print(passed.head(20).to_string(index=False))

print("\n" + "=" * 80)
print("BREAKDOWN BY ASSET CLASS (instruments that passed)")
print("=" * 80)
print(passed.groupby('Asset Class').agg({
    'Instrument': 'count',
    'Sharpe': ['mean', 'max'],
    'Max Position': 'mean'
}).round(2))

print("\n" + "=" * 80)
print("RECOMMENDED 12 INSTRUMENTS FOR DIVERSIFICATION")
print("=" * 80)

# Smart selection: pick best from each asset class
recommendations = []

# Target allocation by asset class
targets = {
    'Bonds': 3,
    'Equities': 2,
    'Energy': 2,
    'Metals': 2,
    'Ags': 2,
    'FX': 1
}

for asset_class, count in targets.items():
    subset = passed[passed['Asset Class'] == asset_class].sort_values('Sharpe', ascending=False)
    recommendations.extend(subset.head(count)['Instrument'].tolist())

print(f"\nSelected {len(recommendations)} instruments:")
for i, inst in enumerate(recommendations, 1):
    row = passed[passed['Instrument'] == inst].iloc[0]
    print(f"{i:>2}. {inst:>15} ({row['Asset Class']:>10}) - SR: {row['Sharpe']:>5.2f}, Max Pos: {row['Max Position']:>6.1f}")

# Save to CSV
df.to_csv('/home/claude/instrument_scan_results.csv', index=False)
print(f"\nFull results saved to: /home/claude/instrument_scan_results.csv")
print("\nNext step: Run backtest with these 12 recommended instruments!")