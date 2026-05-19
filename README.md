# Binance Futures Trading Bot

A simplified Python-based trading bot for Binance Futures Testnet (USDT-M) developed as part of the Primetrade.ai Python Developer Application Task.

---

# Features

- Place MARKET orders
- Place LIMIT orders
- Supports BUY and SELL
- Binance Futures Testnet integration
- CLI-based order execution
- Input validation
- Structured modular codebase
- Logging of requests, responses, and errors
- Exception handling

---

# Project Structure

```bash
trading_bot/
│
├── bot/
│   ├── __init__.py
│   ├── client.py
│   ├── orders.py
│   ├── validators.py
│   └── logging_config.py
│
├── logs/
│   └── trading_bot.log
│
├── cli.py
├── requirements.txt
├── README.md
└── .env
```

---

# Technologies Used

- Python 3.x
- python-binance
- argparse
- logging
- Binance Futures Testnet API

---

# Setup Instructions

## 1. Clone Repository

```bash
git clone <your_repository_url>
cd trading_bot
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Binance Testnet Setup

1. Register on Binance Futures Testnet:
   https://testnet.binancefuture.com

2. Generate API Key and Secret Key

3. Create a `.env` file in project root:

```env
API_KEY=your_api_key
API_SECRET=your_api_secret
```

---

# Running the Bot

## MARKET BUY Order

```bash
python cli.py BTCUSDT BUY MARKET 0.001
```

---

## MARKET SELL Order

```bash
python cli.py BTCUSDT SELL MARKET 0.001
```

---

## LIMIT BUY Order

```bash
python cli.py BTCUSDT BUY LIMIT 0.001 --price 50000
```

---

## LIMIT SELL Order

```bash
python cli.py BTCUSDT SELL LIMIT 0.001 --price 100000
```

---

# Example Output

## MARKET Order

```text
===== ORDER REQUEST =====
Symbol      : BTCUSDT
Side        : BUY
Order Type  : MARKET
Quantity    : 0.001

===== ORDER RESPONSE =====
Order ID     : 13163715005
Status       : NEW
Executed Qty : 0.0000
Avg Price    : 0.00

Order placed successfully!
```

---

# Logging

All API requests, responses, and errors are logged in:

```bash
logs/trading_bot.log
```

Example:

```text
2026-05-19 10:20:15 - INFO - Request => Symbol:BTCUSDT ...
2026-05-19 10:20:16 - INFO - Response => {...}
```

---

# Validation and Error Handling

The application validates:

- Order side (BUY/SELL)
- Order type (MARKET/LIMIT)
- Quantity > 0
- LIMIT price availability
- Invalid API responses
- Network/API exceptions

---

# Assumptions

- User already has Binance Futures Testnet account
- API credentials are valid
- Sufficient virtual balance exists in testnet account

---

# Future Improvements

- Stop-Limit Orders
- OCO Orders
- Grid Trading
- TWAP execution
- Web UI / Dashboard
- Real-time market data streaming
- Docker support

---

# Author

Yashwanth Reddy
