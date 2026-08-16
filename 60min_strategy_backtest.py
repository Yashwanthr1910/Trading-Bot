import yfinance as yf
import pandas as pd
import numpy as np

# =========================
# FINAL STRATEGY SETTINGS
# =========================

CAPITAL = 10000
RISK_PER_TRADE = 0.01
RR = 2

INTERVAL = "60m"
PERIOD = "720d"

RSI_PERIOD = 14
RSI_LONG = 60
RSI_SHORT = 40

ENTRY_START_TIME = "10:00"
LAST_ENTRY_TIME = "14:00"
SQUARE_OFF_TIME = "15:15"

STOCKS = [
    "KEC.NS",
    "NBCC.NS",

    "ACC.NS",
    "AMBUJACEM.NS",

    "IOC.NS",
    "BPCL.NS",
    "GAIL.NS",
    "ONGC.NS",

    "KOTAKBANK.NS",
    "AXISBANK.NS",
    "SBIN.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS"
]


def calculate_rsi(df, period=14):
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

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
        daily["Prev_High"] +
        daily["Prev_Low"] +
        daily["Prev_Close"]
    ) / 3

    daily["BC"] = (
        daily["Prev_High"] +
        daily["Prev_Low"]
    ) / 2

    daily["TC"] = (daily["Pivot"] * 2) - daily["BC"]

    return df.merge(
        daily[["Prev_High", "Prev_Low", "TC", "BC"]],
        left_on="Date",
        right_index=True,
        how="left"
    )


def simulate_exit(future_df, stop, target, trade_type):
    square_off_time = pd.to_datetime(SQUARE_OFF_TIME).time()

    for _, row in future_df.iterrows():
        candle_time = row.name.time()

        if trade_type == "LONG":
            if row["Low"] <= stop:
                return stop, "SL"
            if row["High"] >= target:
                return target, "TARGET"

        if trade_type == "SHORT":
            if row["High"] >= stop:
                return stop, "SL"
            if row["Low"] <= target:
                return target, "TARGET"

        if candle_time >= square_off_time:
            return row["Close"], "EOD_EXIT"

    return future_df.iloc[-1]["Close"], "LAST_EXIT"


def backtest_stock(symbol):
    print(f"\nBacktesting {symbol}...")

    df = yf.download(
        symbol,
        period=PERIOD,
        interval=INTERVAL,
        progress=False,
        auto_adjust=False
    )

    if df.empty:
        print(f"No data found for {symbol}")
        return []

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()
    df = calculate_rsi(df, RSI_PERIOD)
    df = add_daily_levels(df)
    df = df.dropna()

    trades = []
    traded_dates = set()

    entry_start_time = pd.to_datetime(ENTRY_START_TIME).time()
    last_entry_time = pd.to_datetime(LAST_ENTRY_TIME).time()

    for i in range(2, len(df) - 1):
        row = df.iloc[i]
        prev_row = df.iloc[i - 1]
        next_row = df.iloc[i + 1]

        current_date = row["Date"]
        current_time = row.name.time()

        if current_date in traded_dates:
            continue

        if current_time <= entry_start_time or current_time >= last_entry_time:
            continue

        long_condition = (
            row["RSI"] > RSI_LONG and
            row["Close"] > row["TC"] and
            row["Close"] > row["Prev_High"] and
            prev_row["Close"] <= row["Prev_High"]
        )

        if long_condition:
            entry = next_row["Open"]
            stop = prev_row["Low"]
            risk_per_share = entry - stop

            if risk_per_share <= 0:
                continue

            qty = int((CAPITAL * RISK_PER_TRADE) / risk_per_share)

            if qty <= 0:
                continue

            target = entry + risk_per_share * RR
            exit_price, result = simulate_exit(df.iloc[i + 1:], stop, target, "LONG")
            pnl = (exit_price - entry) * qty

            trades.append({
                "Symbol": symbol,
                "Date": current_date,
                "Type": "LONG",
                "Entry_Time": next_row.name,
                "Entry": round(entry, 2),
                "Stop": round(stop, 2),
                "Target": round(target, 2),
                "Qty": qty,
                "Exit": round(exit_price, 2),
                "Result": result,
                "PnL": round(pnl, 2)
            })

            traded_dates.add(current_date)
            continue

        short_condition = (
            row["RSI"] < RSI_SHORT and
            row["Close"] < row["BC"] and
            row["Close"] < row["Prev_Low"] and
            prev_row["Close"] >= row["Prev_Low"]
        )

        if short_condition:
            entry = next_row["Open"]
            stop = prev_row["High"]
            risk_per_share = stop - entry

            if risk_per_share <= 0:
                continue

            qty = int((CAPITAL * RISK_PER_TRADE) / risk_per_share)

            if qty <= 0:
                continue

            target = entry - risk_per_share * RR
            exit_price, result = simulate_exit(df.iloc[i + 1:], stop, target, "SHORT")
            pnl = (entry - exit_price) * qty

            trades.append({
                "Symbol": symbol,
                "Date": current_date,
                "Type": "SHORT",
                "Entry_Time": next_row.name,
                "Entry": round(entry, 2),
                "Stop": round(stop, 2),
                "Target": round(target, 2),
                "Qty": qty,
                "Exit": round(exit_price, 2),
                "Result": result,
                "PnL": round(pnl, 2)
            })

            traded_dates.add(current_date)

    return trades


def analyze_results(results):
    if results.empty:
        print("\nNo trades found.")
        return

    total_trades = len(results)
    wins = len(results[results["PnL"] > 0])
    losses = len(results[results["PnL"] < 0])
    win_rate = wins / total_trades * 100

    total_pnl = results["PnL"].sum()
    gross_profit = results[results["PnL"] > 0]["PnL"].sum()
    gross_loss = abs(results[results["PnL"] < 0]["PnL"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else np.nan

    results["Equity"] = CAPITAL + results["PnL"].cumsum()
    results["Peak"] = results["Equity"].cummax()
    results["Drawdown"] = results["Equity"] - results["Peak"]
    max_drawdown = results["Drawdown"].min()

    print("\n========== FINAL STRATEGY SUMMARY ==========")
    print(f"Capital: ₹{CAPITAL}")
    print(f"Risk Per Trade: {RISK_PER_TRADE * 100:.2f}%")
    print(f"Risk Reward: 1:{RR}")
    print(f"RSI Long Threshold: {RSI_LONG}")
    print(f"RSI Short Threshold: {RSI_SHORT}")
    print(f"Entry Window: {ENTRY_START_TIME} to {LAST_ENTRY_TIME}")
    print(f"Exit Rule: SL / TP / 3:15 PM Square-Off")
    print(f"Total Trades: {total_trades}")
    print(f"Winning Trades: {wins}")
    print(f"Losing Trades: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total PnL: ₹{total_pnl:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Max Drawdown: ₹{max_drawdown:.2f}")


def main():
    print("Final strategy backtest started...")

    all_trades = []

    for stock in STOCKS:
        all_trades.extend(backtest_stock(stock))

    results = pd.DataFrame(all_trades)

    analyze_results(results)


if __name__ == "__main__":
    main()