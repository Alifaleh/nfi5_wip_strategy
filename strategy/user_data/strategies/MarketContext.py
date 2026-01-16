"""
MarketContext - External data integration for contextual trading
Provides Fear & Greed Index and BTC Dominance signals for regime filtering and position sizing.

Usage in backtest: Loads historical CSV data
Usage in live: Fetches live data from APIs with TTLCache
"""

import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from cachetools import TTLCache
import requests

logger = logging.getLogger(__name__)


class MarketContext:
    """
    Singleton class that provides market context data for regime filtering.
    
    Uses:
    - Fear & Greed Index (Alternative.me) - Position sizing modifier
    - BTC Dominance (CoinGecko /global) - Altcoin veto signal
    """
    
    _instance = None
    
    # TTL Caches for live trading (to avoid hitting API rate limits)
    _fng_cache = TTLCache(maxsize=1, ttl=3600)  # 1 hour cache
    _btc_dom_cache = TTLCache(maxsize=1, ttl=600)  # 10 min cache
    
    # Historical data storage
    _fng_history: Optional[pd.DataFrame] = None
    _data_dir: str = '/freqtrade/user_data/data'  # Docker path
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ensure_data_exists()
            cls._instance._load_historical_data()
        return cls._instance
    
    def _ensure_data_exists(self) -> None:
        """
        Ensure F&G historical data exists and is up-to-date.
        Auto-downloads if missing or older than 24 hours.
        """
        import csv
        from datetime import timezone
        
        fng_path = os.path.join(self._data_dir, 'fear_greed_index.csv')
        should_download = False
        
        # Check if file exists
        if not os.path.exists(fng_path):
            logger.info("F&G data file not found, downloading...")
            should_download = True
        else:
            # Check if file is older than 24 hours
            try:
                file_mtime = datetime.fromtimestamp(os.path.getmtime(fng_path), tz=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - file_mtime).total_seconds() / 3600
                if age_hours > 24:
                    logger.info(f"F&G data is {age_hours:.1f}h old, refreshing...")
                    should_download = True
            except Exception as e:
                logger.warning(f"Could not check F&G file age: {e}")
        
        if should_download:
            self._download_fng_data(fng_path)
    
    def _download_fng_data(self, fng_path: str) -> None:
        """Download Fear & Greed historical data from Alternative.me API."""
        import csv
        from datetime import timezone
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(fng_path), exist_ok=True)
            
            logger.info("Fetching Fear & Greed historical data from Alternative.me...")
            resp = requests.get(
                "https://api.alternative.me/fng/?limit=0",
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                entries = data.get('data', [])
                
                with open(fng_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['date', 'value', 'classification'])
                    for entry in entries:
                        ts = int(entry['timestamp'])
                        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d')
                        writer.writerow([date, entry['value'], entry['value_classification']])
                
                logger.info(f"Downloaded {len(entries)} F&G entries to {fng_path}")
            else:
                logger.warning(f"Failed to fetch F&G data: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"Failed to download F&G data: {e}")
    
    def _load_historical_data(self) -> None:
        """Load historical Fear & Greed data for backtesting."""
        fng_path = os.path.join(self._data_dir, 'fear_greed_index.csv')
        
        if os.path.exists(fng_path):
            try:
                self._fng_history = pd.read_csv(fng_path, parse_dates=['date'])
                self._fng_history.set_index('date', inplace=True)
                self._fng_history.sort_index(inplace=True)
                logger.info(f"Loaded {len(self._fng_history)} F&G historical entries")
            except Exception as e:
                logger.warning(f"Failed to load F&G history: {e}")
                self._fng_history = None
        else:
            logger.warning(f"F&G history file not found: {fng_path}")
            self._fng_history = None
    
    def get_fear_greed(self, date: Optional[datetime] = None, is_backtest: bool = False) -> int:
        """
        Get Fear & Greed Index value (0-100).
        
        Args:
            date: Date to lookup (for backtesting). If None, fetches live data.
            is_backtest: If True, uses historical data. If False, fetches live.
            
        Returns:
            Integer 0-100 (0 = Extreme Fear, 100 = Extreme Greed)
            Returns 50 (Neutral) on failure.
        """
        # Backtest mode - use historical data
        if is_backtest and date is not None and self._fng_history is not None:
            return self._get_historical_fng(date)
        
        # Live mode - fetch from API with caching
        return self._fetch_live_fng()
    
    def _get_historical_fng(self, date: datetime) -> int:
        """Lookup historical F&G value for a specific date."""
        if self._fng_history is None:
            return 50  # Neutral fallback
        
        try:
            # Normalize to date without time
            lookup_date = pd.Timestamp(date.date())
            
            # Try exact match first
            if lookup_date in self._fng_history.index:
                return int(self._fng_history.loc[lookup_date, 'value'])
            
            # Find closest previous date
            mask = self._fng_history.index <= lookup_date
            if mask.any():
                closest = self._fng_history.index[mask][-1]
                return int(self._fng_history.loc[closest, 'value'])
            
            return 50  # Fallback if no data
        except Exception as e:
            logger.debug(f"F&G lookup error for {date}: {e}")
            return 50
    
    def _fetch_live_fng(self) -> int:
        """Fetch live Fear & Greed from API with caching."""
        if 'fng' in self._fng_cache:
            return self._fng_cache['fng']
        
        try:
            resp = requests.get(
                'https://api.alternative.me/fng/',
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                value = int(data['data'][0]['value'])
                self._fng_cache['fng'] = value
                return value
        except Exception as e:
            logger.warning(f"Failed to fetch live F&G: {e}")
        
        return 50  # Neutral fallback
    
    def get_btc_dominance(self, is_backtest: bool = False) -> float:
        """
        Get current BTC Dominance percentage.
        
        Note: Historical BTC dominance is not easily available for free.
        For backtesting, we return a neutral 50% which disables the filter.
        For live trading, we fetch from CoinGecko.
        
        Returns:
            Float 0-100 (percentage of total crypto market cap)
        """
        if is_backtest:
            # Historical BTC.D not available for free - return neutral
            return 50.0
        
        return self._fetch_live_btc_dominance()
    
    def _fetch_live_btc_dominance(self) -> float:
        """Fetch live BTC Dominance from CoinGecko."""
        if 'btc_dom' in self._btc_dom_cache:
            return self._btc_dom_cache['btc_dom']
        
        try:
            resp = requests.get(
                'https://api.coingecko.com/api/v3/global',
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                dom = float(data['data']['market_cap_percentage']['btc'])
                self._btc_dom_cache['btc_dom'] = dom
                return dom
        except Exception as e:
            logger.warning(f"Failed to fetch BTC dominance: {e}")
        
        return 50.0  # Neutral fallback
    
    def get_stake_modifier(self, date: Optional[datetime] = None, is_backtest: bool = False) -> float:
        """
        Calculate position size modifier based on Fear & Greed Index.
        
        Returns a multiplier for stake_amount:
        - F&G < 25 (Extreme Fear): 1.5x (buy the fear)
        - F&G 25-45 (Fear): 1.2x
        - F&G 45-55 (Neutral): 1.0x
        - F&G 55-75 (Greed): 0.8x
        - F&G > 75 (Extreme Greed): 0.5x (reduce during euphoria)
        
        Returns:
            Float multiplier (0.5 to 1.5)
        """
        fng = self.get_fear_greed(date, is_backtest)
        
        if fng < 25:
            return 1.5
        elif fng < 45:
            return 1.2
        elif fng < 55:
            return 1.0
        elif fng < 75:
            return 0.8
        else:
            return 0.5
    
    def should_veto_altcoin(self, pair: str, is_backtest: bool = False) -> bool:
        """
        Check if altcoin trade should be vetoed due to high BTC dominance.
        
        When BTC.D > 55%, capital is flowing into BTC as a safe haven.
        Altcoins typically bleed during these periods.
        
        Note: Only active in live trading (historical BTC.D not available).
        
        Args:
            pair: Trading pair (e.g., 'ETH/USDT')
            is_backtest: If True, always returns False (no veto)
            
        Returns:
            bool: True if trade should be vetoed
        """
        # BTC pairs are never vetoed
        if 'BTC' in pair.split('/')[0]:
            return False
        
        # In backtest mode, BTC.D filter is disabled (no free historical data)
        if is_backtest:
            return False
        
        btc_dom = self.get_btc_dominance(is_backtest=False)
        
        # Veto altcoins when BTC dominance > 55%
        if btc_dom > 55.0:
            logger.info(f"VETO {pair}: BTC Dominance at {btc_dom:.1f}% (>55%)")
            return True
        
        return False


# Singleton instance
market_context = MarketContext()
