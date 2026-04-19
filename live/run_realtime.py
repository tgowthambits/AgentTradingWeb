"""
Entry point for real-time trading system
Run this script to start the 5-second interval trading loop
"""

from live.realtime_trader import RealTimeTrader
from loguru import logger

if __name__ == "__main__":
    # Configuration
    QUANTITY = 1  # Number of shares/units per trade
    INTERVAL = 5  # Seconds between checks
    
    logger.info("="*70)
    logger.info(" REAL-TIME TRADING SYSTEM")
    logger.info("="*70)
    logger.info(f"Trading Quantity: {QUANTITY} units")
    logger.info(f"Check Interval: {INTERVAL} seconds")
    logger.info("Strategy: Long-only (no shorting)")
    logger.info("="*70)
    
    # Initialize and start trader
    trader = RealTimeTrader(quantity=QUANTITY, interval=INTERVAL)
    trader.run()

