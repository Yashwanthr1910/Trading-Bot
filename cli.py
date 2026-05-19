import argparse
import traceback

from bot.orders import place_order
from bot.validators import (
    validate_side,
    validate_order_type
)


def main():

    parser = argparse.ArgumentParser(
        description="Binance Futures Testnet Trading Bot"
    )

    parser.add_argument(
        "symbol",
        type=str,
        help="Trading symbol"
    )

    parser.add_argument(
        "side",
        type=str,
        help="BUY or SELL"
    )

    parser.add_argument(
        "order_type",
        type=str,
        help="MARKET or LIMIT"
    )

    parser.add_argument(
        "quantity",
        type=float,
        help="Order quantity"
    )

    parser.add_argument(
        "--price",
        type=float,
        default=None,
        help="Price for LIMIT order"
    )

    args = parser.parse_args()

    try:

        side = validate_side(args.side)

        order_type = validate_order_type(
            args.order_type
        )

        print("\n===== ORDER REQUEST =====")

        print(f"Symbol      : {args.symbol}")
        print(f"Side        : {side}")
        print(f"Order Type  : {order_type}")
        print(f"Quantity    : {args.quantity}")

        if args.price:
            print(f"Price       : {args.price}")

        response = place_order(
            symbol=args.symbol,
            side=side,
            order_type=order_type,
            quantity=args.quantity,
            price=args.price
        )

        print("\n===== ORDER RESPONSE =====")

        print(
            f"Order ID     : "
            f"{response.get('orderId')}"
        )

        print(
            f"Status       : "
            f"{response.get('status')}"
        )

        print(
            f"Executed Qty : "
            f"{response.get('executedQty')}"
        )

        print(
            f"Avg Price    : "
            f"{response.get('avgPrice')}"
        )

        print("\nOrder placed successfully!")

    except Exception:

        print("\n===== ERROR =====\n")

        traceback.print_exc()


if __name__ == "__main__":
    main()