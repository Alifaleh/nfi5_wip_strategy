import pandas as pd
import numpy as np
import os
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

class OnChainOracle:
    """
    Singleton helper class to load and serve on-chain data from DeFiLlama.
    Fetches data from API if local file is missing or stale (> 6 hours).
    """
    _instance = None
    _data = None
    _last_fetched = 0
    _cache_duration = 21600  # 6 hours in seconds
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OnChainOracle, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        # Setup paths
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.data_dir = self.base_dir / 'user_data' / 'data' / 'onchain'
        self.data_path = self.data_dir / 'defillama_data.csv'
        
        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._load_or_fetch_data()
        
    def _load_or_fetch_data(self):
        current_time = time.time()
        
        # Check if file exists and is fresh
        if self.data_path.exists():
            file_mod_time = self.data_path.stat().st_mtime
            if (current_time - file_mod_time) < self._cache_duration:
                # File is fresh, load it
                self._load_from_csv()
                return

        # Fetch new data if missing or stale
        try:
            print("OnChainOracle: Fetching fresh data from DeFiLlama...")
            self._fetch_and_save_data()
            self._load_from_csv()
        except Exception as e:
            print(f"OnChainOracle Error: Failed to fetch data ({e}). Falling back to existing CSV if available.")
            if self.data_path.exists():
                self._load_from_csv()
    
    def _load_from_csv(self):
        try:
            if self.data_path.exists():
                self._data = pd.read_csv(self.data_path)
                self._data['date'] = pd.to_datetime(self._data['date'])
                self._data = self._data.set_index('date').sort_index()
            else:
                self._data = pd.DataFrame()
        except Exception as e:
            print(f"OnChainOracle Error loading CSV: {e}")
            self._data = pd.DataFrame()

    def _fetch_and_save_data(self):
        # 1. TVL
        tvl_url = "https://api.llama.fi/v2/historicalChainTvl"
        resp_tvl = requests.get(tvl_url, timeout=10)
        resp_tvl.raise_for_status()
        df_tvl = pd.DataFrame(resp_tvl.json())
        df_tvl['date'] = pd.to_datetime(df_tvl['date'], unit='s', utc=True)
        df_tvl = df_tvl.set_index('date').rename(columns={'tvl': 'total_tvl'})[['total_tvl']]

        # 2. Stablecoins
        stable_url = "https://stablecoins.llama.fi/stablecoincharts/all"
        resp_stable = requests.get(stable_url, timeout=10)
        resp_stable.raise_for_status()
        df_stable = pd.DataFrame(resp_stable.json())
        df_stable['date'] = pd.to_datetime(df_stable['date'], unit='s', utc=True)
        df_stable = df_stable.set_index('date')
        
        # Extract peggedUSD
        if 'totalCirculating' in df_stable.columns:
            df_stable['stable_mcap'] = df_stable['totalCirculating'].apply(
                lambda x: x.get('peggedUSD', 0) if isinstance(x, dict) else x
            )
            df_stable = df_stable[['stable_mcap']]
        else:
            df_stable = pd.DataFrame()

        # Resample and Merge
        # Freqtrade uses 5m or 1h, but on-chain data is daily. 
        # We resample to 1h to match typical strategy timeframe logic.
        df_tvl_1h = df_tvl.resample('1h').ffill()
        df_stable_1h = df_stable.resample('1h').ffill()
        
        merged = pd.merge(df_tvl_1h, df_stable_1h, left_index=True, right_index=True, how='outer')
        merged = merged.ffill() # Forward fill missing values
        
        # Save
        merged.to_csv(self.data_path)
        print(f"OnChainOracle: Data saved to {self.data_path}")

    def merge_with_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Merges on-chain data into the provided dataframe.
        Checks for stale data periodically (logic can be added here if needed, 
        but usually init load is sufficient for short running cycles).
        """
        # Optional: Auto-refresh if running for a long time (e.g., > 6 hours since last load)
        # But be careful not to trigger on every candle.
        
        if self._data is None or self._data.empty:
            return dataframe
        
        if 'date' not in dataframe.columns:
            return dataframe
            
        dataframe['date'] = pd.to_datetime(dataframe['date'])
        dataframe = dataframe.sort_values('date')
        
        merged = pd.merge_asof(
            dataframe,
            self._data,
            on='date',
            direction='backward'
        )
        
        return merged
