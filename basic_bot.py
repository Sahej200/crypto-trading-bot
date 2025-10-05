#!/usr/bin/env python3

import time
import hmac
import hashlib
import requests
import logging
import argparse
from urllib.parse import urlencode

# -----------------------
# Logging configuration
# -----------------------
logger = logging.getLogger("BasicBot")
logger.setLevel(logging.DEBUG)
fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")

# console
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(fmt)
logger.addHandler(ch)

# file
fh = logging.FileHandler("basic_bot.log")
fh.setLevel(logging.DEBUG)
fh.setFormatter(fmt)
logger.addHandler(fh)


# -----------------------
# BasicBot class
# -----------------------
class BasicBot:
    """
    Minimal Binance Futures (USDT-M) REST client for placing orders on testnet.
    """

    def __init__(self, api_key: str, api_secret: str,
                 base_url: str = "https://testnet.binancefuture.com",
                 recv_window: int = 5000, timeout: int = 10):
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": api_key})
        self.timeout = timeout
        logger.debug(f"Initialized BasicBot with base_url={self.base_url}")

    # ----- helper: sign querystring -----
    def _sign(self, data: dict) -> str:
        """Return signature for a dict of params."""
        query = urlencode(data, doseq=True)
        signature = hmac.new(self.api_secret, query.encode("utf-8"), hashlib.sha256).hexdigest()
        logger.debug(f"Signing query: {query} -> signature: {signature}")
        return signature

    # ----- helper: do signed request -----
    def _signed_request(self, method: str, path: str, payload: dict = None):
        """Make signed request to futures API."""
        payload = payload.copy() if payload else {}
        payload.setdefault("recvWindow", self.recv_window)
        payload["timestamp"] = int(time.time() * 1000)
        signature = self._sign(payload)
        payload["signature"] = signature
        url = f"{self.base_url}{path}"
        logger.info(f"REQUEST -> {method} {url} params={payload}")
        try:
            if method.upper() == "GET":
                r = self.session.get(url, params=payload, timeout=self.timeout)
            elif method.upper() == "POST":
                r = self.session.post(url, params=payload, timeout=self.timeout)
            elif method.upper() == "DELETE":
                r = self.session.delete(url, params=payload, timeout=self.timeout)
            else:
                raise ValueError("Unsupported HTTP method")
        except requests.RequestException:
            logger.exception("Network error during API request")
            raise

        try:
            content = r.json()
        except ValueError:
            content = r.text
        logger.info(f"RESPONSE <- status={r.status_code} body={content}")

        if not r.ok:
            err_msg = content.get("msg") if isinstance(content, dict) else str(content)
            raise RuntimeError(f"API returned error {r.status_code}: {err_msg}")

        return content

    # ----- place order -----
    def place_order(self, symbol: str, side: str, order_type: str,
                    quantity: float = None, price: float = None,
                    time_in_force: str = "GTC", stop_price: float = None,
                    reduce_only: bool = False, close_position: bool = False, position_side: str = None):
        """Place an order on futures (MARKET, LIMIT, STOP_LIMIT)."""
        symbol = symbol.upper()
        side = side.upper()
        order_type = order_type.upper()

        if side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")
        if order_type not in ("MARKET", "LIMIT", "STOP_LIMIT"):
            raise ValueError("order_type must be MARKET, LIMIT or STOP_LIMIT")

        # ---- Fetch exchange info ----
        try:
            info = self._signed_request("GET", "/fapi/v1/exchangeInfo", payload={})
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    filters = {f['filterType']: f for f in s['filters']}
                    min_qty = float(filters['LOT_SIZE']['minQty'])
                    step_size = float(filters['LOT_SIZE']['stepSize'])
                    min_price = float(filters['PRICE_FILTER']['minPrice'])
                    tick_size = float(filters['PRICE_FILTER']['tickSize'])
                    break
            else:
                raise ValueError(f"Symbol {symbol} not found in exchangeInfo")
        except Exception as e:
            logger.warning(f"Could not fetch exchange info: {e}")
            min_qty, step_size, min_price, tick_size = 0.001, 0.001, 0.01, 0.01

        # ---- Round to valid steps ----
        def round_step(value, step):
            return round(value / step) * step

        if quantity:
            quantity = max(min_qty, round_step(quantity, step_size))
        if price:
            price = max(min_price, round_step(price, tick_size))
        logger.info(f"Adjusted quantity={quantity}, price={price}")

        # ---- Build params ----
        params = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "reduceOnly": str(reduce_only).lower(),
            "closePosition": str(close_position).lower(),
        }

        if position_side:
            params["positionSide"] = position_side

        if order_type == "MARKET":
            params["type"] = "MARKET"
        elif order_type == "LIMIT":
            params.update({
                "type": "LIMIT",
                "price": price,
                "timeInForce": time_in_force
            })
        elif order_type == "STOP_LIMIT":
            params.update({
                "type": "STOP",
                "price": price,
                "stopPrice": stop_price,
                "timeInForce": time_in_force
            })

        params = {k: v for k, v in params.items() if v is not None}

        return self._signed_request("POST", "/fapi/v1/order", payload=params)

    # ----- get order status -----
    def get_order(self, symbol: str, order_id: int = None, orig_client_order_id: str = None):
        """Query an order by orderId or origClientOrderId."""
        if not (order_id or orig_client_order_id):
            raise ValueError("Either order_id or orig_client_order_id must be provided")
        params = {"symbol": symbol.upper()}
        if order_id:
            params["orderId"] = int(order_id)
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id
        return self._signed_request("GET", "/fapi/v1/order", payload=params)

    # ----- cancel order -----
    def cancel_order(self, symbol: str, order_id: int = None, orig_client_order_id: str = None):
        """Cancel an active order by orderId or origClientOrderId."""
        if not (order_id or orig_client_order_id):
            raise ValueError("Either order_id or orig_client_order_id must be provided")
        params = {"symbol": symbol.upper()}
        if order_id:
            params["orderId"] = int(order_id)
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id
        return self._signed_request("DELETE", "/fapi/v1/order", payload=params)


# -----------------------
# CLI handling
# -----------------------
def parse_args():
    p = argparse.ArgumentParser(description="Basic Binance Futures Testnet Trading Bot CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    order_p = sub.add_parser("order", help="Place an order")
    order_p.add_argument("--api-key", required=True)
    order_p.add_argument("--api-secret", required=True)
    order_p.add_argument("--base-url", default="https://testnet.binancefuture.com")
    order_p.add_argument("--symbol", required=True)
    order_p.add_argument("--side", required=True, choices=["BUY", "SELL"])
    order_p.add_argument("--type", required=True, choices=["MARKET", "LIMIT", "STOP_LIMIT"])
    order_p.add_argument("--quantity", type=float)
    order_p.add_argument("--price", type=float)
    order_p.add_argument("--stop-price", type=float)
    order_p.add_argument("--time-in-force", default="GTC")
    order_p.add_argument("--reduce-only", action="store_true")
    order_p.add_argument("--close-position", action="store_true")
    order_p.add_argument("--position-side", help="BOTH/LONG/SHORT")

    q_p = sub.add_parser("query", help="Query order status")
    q_p.add_argument("--api-key", required=True)
    q_p.add_argument("--api-secret", required=True)
    q_p.add_argument("--base-url", default="https://testnet.binancefuture.com")
    q_p.add_argument("--symbol", required=True)
    q_p.add_argument("--order-id", type=int)
    q_p.add_argument("--orig-client-order-id", type=str)

    c_p = sub.add_parser("cancel", help="Cancel order")
    c_p.add_argument("--api-key", required=True)
    c_p.add_argument("--api-secret", required=True)
    c_p.add_argument("--base-url", default="https://testnet.binancefuture.com")
    c_p.add_argument("--symbol", required=True)
    c_p.add_argument("--order-id", type=int)
    c_p.add_argument("--orig-client-order-id", type=str)

    return p.parse_args()


def main():
    args = parse_args()

    bot = BasicBot(args.api_key, args.api_secret, base_url=args.base_url)

    try:
        if args.cmd == "order":
            resp = bot.place_order(
                symbol=args.symbol,
                side=args.side,
                order_type=args.type,
                quantity=args.quantity,
                price=args.price,
                time_in_force=args.time_in_force,
                stop_price=args.stop_price,
                reduce_only=args.reduce_only,
                close_position=args.close_position,
                position_side=args.position_side
            )
            print("Order response:\n", resp)
        elif args.cmd == "query":
            resp = bot.get_order(symbol=args.symbol, order_id=args.order_id, orig_client_order_id=args.orig_client_order_id)
            print("Order info:\n", resp)
        elif args.cmd == "cancel":
            resp = bot.cancel_order(symbol=args.symbol, order_id=args.order_id, orig_client_order_id=args.orig_client_order_id)
            print("Cancel response:\n", resp)
    except Exception as e:
        logger.exception("Error during execution")
        print("Error:", e)


if __name__ == "__main__":
    main()
