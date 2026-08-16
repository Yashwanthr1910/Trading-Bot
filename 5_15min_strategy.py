import yfinance as yf
import pandas as pd
import numpy as np

# =========================
# SETTINGS
# =========================

CAPITAL = 10000
RISK_PER_TRADE = 0.01
RR = 2

INTERVAL = "15m"
PERIOD = "60d"

RSI_PERIOD = 14
RSI_LONG = 60
RSI_SHORT = 40

ENTRY_START_TIME = "10:00"
LAST_ENTRY_TIME = "14:30"
SQUARE_OFF_TIME = "15:15"

STOCKS = [
    "ULTRACEMCO.NS",
    "GRASIM.NS",
    "SHREECEM.NS",
    "AMBUJACEM.NS",
    "ACC.NS",

    "VOLTAS.NS",
    "WHIRLPOOL.NS",
    "BLUESTARCO.NS",
    "DIXON.NS",
    "HAVELLS.NS",

    "LT.NS",
    "NBCC.NS",
    "KEC.NS",
    "IRB.NS",
    "PNCINFRA.NS",

    "ICICIBANK.NS",
    "SBIN.NS",
    "HDFCBANK.NS",
    "LICHSGFIN.NS",
    "INDIANB.NS",

    "ONGC.NS",
    "BPCL.NS",
    "IOC.NS",
    "HINDPETRO.NS",
    "GAIL.NS"
]

# =========================
# INDICATORS
# =========================

def calculate_rsi(df):
    delta = df["Close"].diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(RSI_PERIOD).mean()
    avg_loss = loss.rolling(RSI_PERIOD).mean()

    rs = avg_gain / avg_loss

    df["RSI"] = 100 - (100 / (1 + rs))

    return df


def add_daily_levels(df):
    df["Date"] = df.index.date

    daily = df.groupby("Date").agg({
        "High": "max",
        "Low": "min",
        "Close": "last"
    })

    daily["Prev_High"] = daily["High"].shift(1)
    daily["Prev_Low"] = daily["Low"].shift(1)
    daily["Prev_Close"] = daily["Close"].shift(1)

    daily["Pivot"] = (
        daily["Prev_High"]
        + daily["Prev_Low"]
        + daily["Prev_Close"]
    ) / 3

    daily["BC"] = (
        daily["Prev_High"]
        + daily["Prev_Low"]
    ) / 2

    daily["TC"] = (
        daily["Pivot"] * 2
    ) - daily["BC"]

    df = df.merge(
        daily[["Prev_High", "Prev_Low", "TC", "BC"]],
        left_on="Date",
        right_index=True,
        how="left"
    )

    return df


# =========================
# EXIT LOGIC
# =========================

def simulate_exit(future_df, stop, target, trade_type):
    square_off = pd.to_datetime(SQUARE_OFF_TIME).time()

    for _, row in future_df.iterrows():

        if trade_type == "LONG":

            if row["Low"] <= stop:
                return stop, "SL"

            if row["High"] >= target:
                return target, "TARGET"

        else:

            if row["High"] >= stop:
                return stop, "SL"

            if row["Low"] <= target:
                return target, "TARGET"

        if row.name.time() >= square_off:
            return row["Close"], "EOD_EXIT"

    return future_df.iloc[-1]["Close"], "LAST_EXIT"


# =========================
# BACKTEST
# =========================

def backtest_stock(symbol):

    print(f"Backtesting {symbol}")

    df = yf.download(
        symbol,
        period=PERIOD,
        interval=INTERVAL,
        progress=False,
        auto_adjust=False
    )

    if df.empty:
        return []

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()

    df = calculate_rsi(df)
    df = add_daily_levels(df)

    df = df.dropna()

    trades = []

    traded_dates = set()

    for i in range(2, len(df)-1):

        row = df.iloc[i]
        prev = df.iloc[i-1]
        nxt = df.iloc[i+1]

        current_date = row["Date"]
        current_time = row.name.time()

        if current_date in traded_dates:
            continue

        if current_time <= pd.to_datetime(ENTRY_START_TIME).time():
            continue

        if current_time >= pd.to_datetime(LAST_ENTRY_TIME).time():
            continue

        # LONG

        long_cond = (
            row["RSI"] > RSI_LONG and
            row["Close"] > row["TC"] and
            row["Close"] > row["Prev_High"] and
            prev["Close"] <= row["Prev_High"]
        )

        if long_cond:

            entry = nxt["Open"]
            stop = prev["Low"]

            risk = entry - stop

            if risk <= 0:
                continue

            qty = int((CAPITAL * RISK_PER_TRADE) / risk)

            if qty <= 0:
                continue

            target = entry + risk * RR

            exit_price, result = simulate_exit(
                df.iloc[i+1:],
                stop,
                target,
                "LONG"
            )

            pnl = (exit_price - entry) * qty

            trades.append({
                "Symbol": symbol,
                "Date": current_date,
                "Type": "LONG",
                "PnL": round(pnl, 2)
            })

            traded_dates.add(current_date)

            continue

        # SHORT

        short_cond = (
            row["RSI"] < RSI_SHORT and
            row["Close"] < row["BC"] and
            row["Close"] < row["Prev_Low"] and
            prev["Close"] >= row["Prev_Low"]
        )

        if short_cond:

            entry = nxt["Open"]
            stop = prev["High"]

            risk = stop - entry

            if risk <= 0:
                continue

            qty = int((CAPITAL * RISK_PER_TRADE) / risk)

            if qty <= 0:
                continue

            target = entry - risk * RR

            exit_price, result = simulate_exit(
                df.iloc[i+1:],
                stop,
                target,
                "SHORT"
            )

            pnl = (entry - exit_price) * qty

            trades.append({
                "Symbol": symbol,
                "Date": current_date,
                "Type": "SHORT",
                "PnL": round(pnl, 2)
            })

            traded_dates.add(current_date)

    return trades


# =========================
# SUMMARY
# =========================

def analyze(results):

    if results.empty:
        print("No trades found.")
        return

    total = len(results)

    wins = len(results[results["PnL"] > 0])
    losses = len(results[results["PnL"] < 0])

    win_rate = wins / total * 100

    total_pnl = results["PnL"].sum()

    gross_profit = results[results["PnL"] > 0]["PnL"].sum()
    gross_loss = abs(results[results["PnL"] < 0]["PnL"].sum())

    pf = gross_profit / gross_loss

    equity = CAPITAL + results["PnL"].cumsum()

    drawdown = equity - equity.cummax()

    print("\n===== SUMMARY =====")

    print("Total Trades :", total)
    print("Winning Trades :", wins)
    print("Losing Trades :", losses)

    print("Win Rate :", round(win_rate, 2), "%")
    print("Total PnL : ₹", round(total_pnl, 2))

    print("Profit Factor :", round(pf, 2))

    print("Max Drawdown : ₹", round(drawdown.min(), 2))


# =========================
# MAIN
# =========================

all_trades = []

print("Sector Filtered Backtest Started...\n")

for stock in STOCKS:
    all_trades.extend(backtest_stock(stock))

results = pd.DataFrame(all_trades)

analyze(results)