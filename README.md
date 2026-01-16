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

## Notes

- **On-Chain Data**: The strategy uses `OnChainOracle` which auto-downloads data to `user_data/data/onchain/defillama_data.csv`. Internet access is required on container startup.
- **Pairlists**:
  - `config_live.json` uses a **VolumePairList** (dynamically selects top coins).
  - `config_backtest.json` uses a **StaticPairList** (fixed set of 40+ coins).
- Ensure Docker is properly installed and running before executing any commands.

### Maintainers

[Ali Faleh](https://github.com/alifaleh).
