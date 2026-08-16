import yfinance as yf
import pandas as pd
import numpy as np

# =========================
# SETTINGS
# =========================

CAPITAL = 10000
RISK_PER_TRADE = 0.01

INTERVAL = "1m"
PERIOD = "7d"

RSI_PERIOD = 14
RSI_LONG = 60
RSI_SHORT = 40

ENTRY_START_TIME = "10:00"
LAST_ENTRY_TIME = "14:00"
SQUARE_OFF_TIME = "15:15"

EQUITY_RR = 2
FNO_RR = 3

EQUITY_CAPITAL_SHARE = 0.40
FNO_CAPITAL_SHARE = 0.60

FNO_LEVERAGE = 5

STOCKS = [
    "ICICIBANK.NS",
    "LICHSGFIN.NS",
    "INDIANB.NS",
    "ONGC.NS",
    "ULTRACEMCO.NS",
    "GAIL.NS",
    "HDFCBANK.NS",
    "LT.NS",
    "AMBUJACEM.NS",
    "DIXON.NS"
]


# =========================
# INDICATORS
# =========================

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
    square_off_time = pd.to_datetime(SQUARE_OFF_TIME).time()

    for _, row in future_df.iterrows():
        candle_time = row.name.time()

        if trade_type == "LONG":
            if row["Low"] <= stop:
                return stop, "SL"

            if row["High"] >= target:
                return target, "TARGET"

        elif trade_type == "SHORT":
            if row["High"] >= stop:
                return stop, "SL"

            if row["Low"] <= target:
                return target, "TARGET"

        if candle_time >= square_off_time:
            return row["Close"], "EOD_EXIT"

    return future_df.iloc[-1]["Close"], "LAST_EXIT"


# =========================
# BACKTEST STOCK
# =========================

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

        # =========================
        # LONG CONDITION
        # =========================

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

            equity_risk_amount = CAPITAL * RISK_PER_TRADE * EQUITY_CAPITAL_SHARE
            fno_risk_amount = CAPITAL * RISK_PER_TRADE * FNO_CAPITAL_SHARE

            equity_qty = int(equity_risk_amount / risk_per_share)
            fno_qty = int((fno_risk_amount * FNO_LEVERAGE) / risk_per_share)

            if equity_qty <= 0 or fno_qty <= 0:
                continue

            equity_target = entry + (risk_per_share * EQUITY_RR)
            fno_target = entry + (risk_per_share * FNO_RR)

            equity_exit, equity_result = simulate_exit(
                df.iloc[i + 1:],
                stop,
                equity_target,
                "LONG"
            )

            fno_exit, fno_result = simulate_exit(
                df.iloc[i + 1:],
                stop,
                fno_target,
                "LONG"
            )

            equity_pnl = (equity_exit - entry) * equity_qty
            fno_pnl = (fno_exit - entry) * fno_qty
            total_pnl = equity_pnl + fno_pnl

            trades.append({
                "Symbol": symbol,
                "Date": current_date,
                "Type": "LONG",
                "Signal_Time": row.name,
                "Entry_Time": next_row.name,
                "Entry": round(entry, 2),
                "Stop": round(stop, 2),
                "Risk_Per_Share": round(risk_per_share, 2),

                "Equity_Qty": equity_qty,
                "Equity_Target": round(equity_target, 2),
                "Equity_Exit": round(equity_exit, 2),
                "Equity_Result": equity_result,
                "Equity_PnL": round(equity_pnl, 2),

                "FNO_Qty": fno_qty,
                "FNO_Target": round(fno_target, 2),
                "FNO_Exit": round(fno_exit, 2),
                "FNO_Result": fno_result,
                "FNO_PnL": round(fno_pnl, 2),

                "Total_PnL": round(total_pnl, 2)
            })

            traded_dates.add(current_date)
            continue

        # =========================
        # SHORT CONDITION
        # =========================

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

            equity_risk_amount = CAPITAL * RISK_PER_TRADE * EQUITY_CAPITAL_SHARE
            fno_risk_amount = CAPITAL * RISK_PER_TRADE * FNO_CAPITAL_SHARE

            equity_qty = int(equity_risk_amount / risk_per_share)
            fno_qty = int((fno_risk_amount * FNO_LEVERAGE) / risk_per_share)

            if equity_qty <= 0 or fno_qty <= 0:
                continue

            equity_target = entry - (risk_per_share * EQUITY_RR)
            fno_target = entry - (risk_per_share * FNO_RR)

            equity_exit, equity_result = simulate_exit(
                df.iloc[i + 1:],
                stop,
                equity_target,
                "SHORT"
            )

            fno_exit, fno_result = simulate_exit(
                df.iloc[i + 1:],
                stop,
                fno_target,
                "SHORT"
            )

            equity_pnl = (entry - equity_exit) * equity_qty
            fno_pnl = (entry - fno_exit) * fno_qty
            total_pnl = equity_pnl + fno_pnl

            trades.append({
                "Symbol": symbol,
                "Date": current_date,
                "Type": "SHORT",
                "Signal_Time": row.name,
                "Entry_Time": next_row.name,
                "Entry": round(entry, 2),
                "Stop": round(stop, 2),
                "Risk_Per_Share": round(risk_per_share, 2),

                "Equity_Qty": equity_qty,
                "Equity_Target": round(equity_target, 2),
                "Equity_Exit": round(equity_exit, 2),
                "Equity_Result": equity_result,
                "Equity_PnL": round(equity_pnl, 2),

                "FNO_Qty": fno_qty,
                "FNO_Target": round(fno_target, 2),
                "FNO_Exit": round(fno_exit, 2),
                "FNO_Result": fno_result,
                "FNO_PnL": round(fno_pnl, 2),

                "Total_PnL": round(total_pnl, 2)
            })

            traded_dates.add(current_date)
            continue

    return trades


# =========================
# ANALYSIS
# =========================

def calculate_metrics(results, pnl_col):
    total_trades = len(results)

    wins = len(results[results[pnl_col] > 0])
    losses = len(results[results[pnl_col] < 0])

    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

    total_pnl = results[pnl_col].sum()
    avg_pnl = results[pnl_col].mean()

    gross_profit = results[results[pnl_col] > 0][pnl_col].sum()
    gross_loss = abs(results[results[pnl_col] < 0][pnl_col].sum())

    pf = gross_profit / gross_loss if gross_loss != 0 else np.nan

    equity = CAPITAL + results[pnl_col].cumsum()
    peak = equity.cummax()
    drawdown = equity - peak

    max_dd = drawdown.min()

    return {
        "Trades": total_trades,
        "Wins": wins,
        "Losses": losses,
        "Win Rate": round(win_rate, 2),
        "Total PnL": round(total_pnl, 2),
        "Average PnL": round(avg_pnl, 2),
        "Profit Factor": round(pf, 2) if not np.isnan(pf) else "NA",
        "Max Drawdown": round(max_dd, 2)
    }


def analyze_results(results):
    if results.empty:
        print("\nNo trades found.")
        return

    results["Combined_Equity"] = CAPITAL + results["Total_PnL"].cumsum()
    results["Peak"] = results["Combined_Equity"].cummax()
    results["Drawdown"] = results["Combined_Equity"] - results["Peak"]

    print("\n========== TRADE RESULTS ==========")
    print(results)

    print("\n========== EQUITY ONLY SUMMARY ==========")
    equity_summary = calculate_metrics(results, "Equity_PnL")
    for k, v in equity_summary.items():
        print(f"{k}: {v}")

    print("\n========== FNO ONLY SUMMARY ==========")
    fno_summary = calculate_metrics(results, "FNO_PnL")
    for k, v in fno_summary.items():
        print(f"{k}: {v}")

    print("\n========== COMBINED EQUITY + FNO SUMMARY ==========")
    combined_summary = calculate_metrics(results, "Total_PnL")
    for k, v in combined_summary.items():
        print(f"{k}: {v}")

    print("\n========== STOCK-WISE COMBINED SUMMARY ==========")
    stock_summary = results.groupby("Symbol").agg(
        Trades=("Total_PnL", "count"),
        Total_PnL=("Total_PnL", "sum"),
        Equity_PnL=("Equity_PnL", "sum"),
        FNO_PnL=("FNO_PnL", "sum"),
        Avg_PnL=("Total_PnL", "mean")
    ).sort_values(by="Total_PnL", ascending=False)

    print(stock_summary)

    print("\n========== RESULT TYPE SUMMARY ==========")
    print("Equity Results:")
    print(results["Equity_Result"].value_counts())

    print("\nFNO Results:")
    print(results["FNO_Result"].value_counts())

    results.to_csv("equity_plus_fno_backtest_results.csv", index=False)
    print("\nResults saved to equity_plus_fno_backtest_results.csv")


# =========================
# MAIN
# =========================

def main():
    print("Equity + FNO backtest started...")

    all_trades = []

    for stock in STOCKS:
        trades = backtest_stock(stock)
        all_trades.extend(trades)

    results = pd.DataFrame(all_trades)

    analyze_results(results)


if __name__ == "__main__":
    main()