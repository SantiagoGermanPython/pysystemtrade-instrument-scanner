# pysystemtrade Instrument Scanner

Scans all available futures instruments in pysystemtrade, applies Rob Carver's granularity test at $1M capital, and recommends a diversified 12-instrument portfolio by asset class.

## What it does

- Tests every instrument for minimum position size viability at $1M notional capital
- Calculates Sharpe ratio and data history for each instrument
- Categorises instruments by asset class: Bonds, Equities, Energy, Metals, Ags, FX, Vol
- Selects the best instruments per class to build a diversified portfolio

## Stack

Python, pysystemtrade, pandas

## Output

Recommended 12-instrument portfolio covering bonds, FX, equities, metals, energy, and agriculture, used as the basis for a live systematic futures trading system on Interactive Brokers.
