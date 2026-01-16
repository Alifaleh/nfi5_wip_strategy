import pandas as pd
import numpy as np
import os
from pathlib import Path

class OnChainOracle:
    """
    Singleton helper class to load and serve on-chain data from DeFiLlama.
    """
    _instance = None
    _data = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OnChainOracle, cls).__new__(cls)
            cls._instance._load_data()
        return cls._instance
    
    def _load_data(self):
        try:
            # Assuming file is in user_data/data/onchain/defillama_data.csv
            # We determine path relative to this file
            base_dir = Path(__file__).parent.parent
            data_path = base_dir / 'data' / 'onchain' / 'defillama_data.csv'
            
            if data_path.exists():
                print(f"Loading on-chain data from {data_path}")
                self._data = pd.read_csv(data_path)
                self._data['date'] = pd.to_datetime(self._data['date'])
                self._data = self._data.set_index('date').sort_index()
            else:
                print(f"Warning: On-chain data not found at {data_path}")
                self._data = pd.DataFrame()
        except Exception as e:
            print(f"Error loading on-chain data: {e}")
            self._data = pd.DataFrame()

    def merge_with_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Merges on-chain data into the provided dataframe based on the 'date' column.
        """
        if self._data is None or self._data.empty:
            return dataframe
        
        # Check if running in backtest or live (Freqtrade dataframes usually have 'date')
        if 'date' not in dataframe.columns:
            return dataframe
            
        # Store original index if needed (though usually RangeIndex)
        
        # We perform a merge_asof or simple join.
        # Since on-chain data is hourly (from our download script), and candles might be 5m,
        # we want to map each candle to the latest available on-chain data point.
        # merge_asof with direction='backward' is appropriate to avoid lookahead if timestamps match exactly,
        # but our script aligned data to hour start.
        # If candle is 10:05, and onchain is 10:00 (generated from data known at 10:00 or end of day?), 
        # using backward search is safe.
        
        # Ensure types match
        dataframe['date'] = pd.to_datetime(dataframe['date'])
        
        # Sort for merge_asof
        dataframe = dataframe.sort_values('date')
        
        merged = pd.merge_asof(
            dataframe,
            self._data,
            on='date',
            direction='backward'
            # tolerance could be added but we accept stale data if needed
        )
        
        return merged
