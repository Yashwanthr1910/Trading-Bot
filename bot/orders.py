from bot.client import client
from bot.logging_config import logger

from binance.exceptions import BinanceAPIException


def place_order(
    symbol,
    side,
    order_type,
    quantity,
    price=None
):

    try:

        logger.info(
            f"Order Request -> "
            f"Symbol: {symbol}, "
            f"Side: {side}, "
            f"Type: {order_type}, "
            f"Quantity: {quantity}, "
            f"Price: {price}"
        )

        params = {
            "symbol": symbol.upper(),
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        # LIMIT ORDER
        if order_type == "LIMIT":

            if price is None:
                raise ValueError(
                    "Price is required for LIMIT order"
                )

            params["price"] = price
            params["timeInForce"] = "GTC"

        response = client.futures_create_order(
            **params
        )

        logger.info(
            f"API Response -> {response}"
        )

        return response

    except BinanceAPIException as e:

        logger.error(
            f"Binance API Error -> {e}"
        )

        raise

    except Exception as e:

        logger.error(
            f"Unexpected Error -> {e}"
        )

        raise