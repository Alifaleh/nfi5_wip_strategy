# Setting NFI5MOHO Strategy with Docker

## Strategy Overview

**NFI5MOHO_WIP** is an advanced Freqtrade strategy incorporating **On-Chain Data Analysis** (DeFiLlama TVL & Stablecoin Velocity) to filter entries based on market risk regimes.

## Docker Installation

Follow these steps to install Docker on your system:

1. **Update your package index:**

   ```bash
   sudo apt update
   ```

2. **Install required packages:**

   ```bash
   sudo apt install apt-transport-https ca-certificates curl software-properties-common
   ```

3. **Add Docker's official GPG key:**

   ```bash
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
   ```

4. **Set up the Docker repository:**

   ```bash
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   ```

5. **Update your package index again:**

   ```bash
   sudo apt update
   ```

6. **Check available Docker versions:**

   ```bash
   apt-cache policy docker-ce
   ```

7. **Install Docker:**

   ```bash
   sudo apt install docker-ce
   ```

8. **Verify Docker is running:**

   ```bash
   sudo systemctl status docker
   ```

9. **Allow non-root users to manage Docker:**

   ```bash
   sudo usermod -aG docker ${USER}
   ```

   Restart your terminal or log out and log back in to apply the changes.

## Strategy Installation

Clone the repository and set up the environment:

1. **Clone the repository:**

   ```bash
   git clone git@github.com:Alifaleh/nfi5_wip_strategy.git
   ```

2. **Navigate to the project directory:**

   ```bash
   cd nfi5_wip_strategy
   ```

3. **Set up Environment Variables:**
   Copy the example environment file:

   ```bash
   cp example.env .env
   ```

   (Edit .env if you need to set specific tags or ports)

4. **Pull the required Docker images & Build:**

   ```bash
   docker compose pull
   docker compose build
   ```

5. **Start the server:**

   ```bash
   docker compose up -d
   ```

   The system should now be running in the background. The **On-Chain Oracle** will automatically fetch required data (TVL/Stablecoins) on startup if local data is stale (>6 hours).

## Useful FreqTrade Commands

Below are some essential commands to help you configure and run your trading bot.

### Configuration Files

- **Live/Dry Run**: `user_data/strategies_config/config_live.json` (Inherits Volume Pairlist)
- **Backtest**: `user_data/strategies_config/config_backtest.json` (Inherits Static Pairlist)

### Download Historical Data

Download historical data using the **Backtest** configuration (Static Pairlist):

```bash
docker compose run --rm freqtrade_nfi5 download-data --config user_data/strategies_config/config_backtest.json --timerange=20240101- --timeframes 5m 1h
```

### Backtest Your Strategy

Evaluate your strategy's performance using historical data:

```bash
docker compose run --rm freqtrade_nfi5 backtesting --config user_data/strategies_config/config_backtest.json --strategy NFI5MOHO_WIP --timerange=20240601-20240701
```

### Run the Bot (Manual Start)

Start the trading bot in live/dry-run mode (using `config_live.json` by default via docker-compose):

```bash
docker compose up -d
```

### View Logs

```bash
docker compose logs -f freqtrade_nfi5
```

## NFI5MOHO_WIP Strategy Documentation

### Overview

**NFI5MOHO_WIP** is a hybrid high-frequency trading strategy that combines the mean-reversion logic of **NostalgiaForInfinity (NFI)** with the precision entry filters of **NASOSv4**. It is designed for spot trading with a focus on catching dips in strong assets while rigorously filtering out "falling knives" and "toxic tops."

**Key Characteristics:**

- **Type:** Mean Reversion + Trend Following Hybrid
- **Timeframe:** 5 Minutes
- **Safety Focus:** Extreme. Prioritizes capital preservation over frequency.
- **Order Management:** Dynamic DCA (Dollar Cost Averaging) + Dynamic Exits.

### 1. Core Logic & Entry Strategy

The strategy acts as a "Sniper," waiting for specific oversold conditions within defined market regimes.

#### A. Primary Engine: NFI Multi-Offset (NostalgiaForInfinity)

The core engine uses 19 different buy conditions (Logic 1-19) based on **Moving Average Offsets**.

- **Concept:** Buy when price drops significantly below a moving average (EMA, SMA, T3, TRIMA, KAMA) by a specific percentage.
- **Example (Logic 1):** Buy if Price < EMA200 * 0.98 AND RSI is low AND MFI is low.
- **Adaptability:** Different logic points target different depths of dips (mild pullbacks vs. crash dips).

#### B. Precision Booster: NASOSv4 "Alpha"

Integrated from the high-performing NASOS strategy to catch scalps in strong trends.

- **Logic:** `RSI_Fast (4) < 35` AND `Price < EMA_8` AND `EWO > 2.0`.
- **Goal:** Buy short-term oversold conditions when the broader momentum (EWO) is still bullish.

### 2. Safety Mechanisms (The "Shield")

This is the most critical part of the strategy. It employs a multi-layered defense system to block risky trades.

#### A. Regime-Aware Dip Detection (Adaptive Z-Score)

- **What it does:** Calculates the Z-Score (standard deviation from mean) of price over the last 3 hours.

- **Logic:** `z_score < -1.75`.
- **Why:** Instead of a fixed percentage drop (e.g., -5%), it requires a *statistical anomaly*. In calm markets, a small drop triggers it. In volatile markets, a huge drop is required. This adapts to market conditions automatically.

#### B. Toxic Top Filter (VWAP Z-Score)

- **What it does:** Checks how far price is above the Volume Weighted Average Price (VWAP).

- **Logic:** Veto entry if `VWAP Z-Score > 3.0`.
- **Why:** If price is 3 standard deviations above VWAP, it is statistically overextended. Buying here is chasing a pump (FOMO), which usually leads to losses.

#### C. "Anti-Falling Knife" (Green Candle Confirmation)

- **What it does:** Vetoes DCA buy orders if the current candle is RED.

- **Logic:** `close > open`.
- **Why:** Ensures the falling price has paused or started to reverse before committing more funds.

#### D. Pump Protection (7-Day & 24H)

- **What it does:** Checks recent price history for massive pumps.

- **Logic:** Veto if `pct_change_7d > 50%`.
- **Why:** Prevents buying into assets that have already parabolicly pumped and are due for a correction.

#### E. On-Chain Risk Detector (Stablecoin Velocity)

- **What it does:** Monitors the flow of Stablecoins and TVL (Total Value Locked) via an Oracle (if connected).

- **Logic:** `risk_off = True` if Stablecoin Velocity is negative (money leaving the ecosystem).
- **Why:** Blocks all buying during liquidity crises or market-wide crashes.

### 3. Order Management (The "Manager")

#### A. Dynamic DCA (Dollar Cost Averaging)

The strategy uses a smart "safety net" to manage trades that go against the initial entry.

- **Capacity:** Max 2 active trades. Each trade is split into 3 "slots" (1 Initial + 2 DCA).
- **Stake Sizing:**
  - **Entry 1:** 33% of allocated capital.
  - **Entry 2 (DCA 1):** 33% added if price drops `1.5x ATR`.
  - **Entry 3 (DCA 2):** 33% added if price drops `4.0x ATR`.
- **Feature:** **ATR-Based Spacing**. The distance between buys is not fixed (e.g., -3%). It expands in volatile markets (e.g., -8%) and contracts in stable markets (e.g., -1%), preventing early entry during a crash.

#### B. Exit Strategy (Profit Taking)

The strategy intentionally disables indicator-based sell signals to avoid cutting winners early ("weak hands").

- **1. Dynamic ROI (Take Profit):** A tiered table that accepts lower profit targets as time passes.
  - *0 min:* +6%
  - *30 min:* +3%
  - *2 hrs:* +1.5%
  - *12 hrs:* +0.5%
  - *Boost:* If a strong trend is detected (RMI or Candle Trend), ROI targets are raised to let winners run.
- **2. Chandelier Exit (Trailing Stop):**
  - **Logic:** If Profit > 1.5%, activate trailing stop.
  - **Stop Price:** `Max_Price_Reached - (2.0 * ATR)`.
  - **Why:** Locks in profits dynamically. If price keeps going up, the stop moves up. If it reverses by 2x ATR, it sells.

### 4. Technical Configuration

- **Max Open Trades:** 2 (Configured via `.env` variable `FREQTRADE__MAX_OPEN_TRADES`).

- **Stake Amount:** Unlimited (Splits balance evenly).
- **Lookahead Bias:** STRICTLY FIXED. All custom logic uses `searchsorted(side='left') - 1` to ensure only closed candle data is used.

## Notes

- **On-Chain Data**: The strategy uses `OnChainOracle` which auto-downloads data to `user_data/data/onchain/defillama_data.csv`. Internet access is required on container startup.
- **Pairlists**:
  - `config_live.json` uses a **VolumePairList** (dynamically selects top coins).
  - `config_backtest.json` uses a **StaticPairList** (fixed set of 40+ coins).
- Ensure Docker is properly installed and running before executing any commands.

### Maintainers

[Ali Faleh](https://github.com/alifaleh).
