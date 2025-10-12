import logging
import alpaca_trade_api as tradeapi

class Broker:
    def __init__(self, key, secret, base_url, mode='paper'):
        self.api = tradeapi.REST(key, secret, base_url, api_version='v2')
        self.mode = mode

    def account(self):
        return self.api.get_account()

    def get_position_qty(self, symbol):
        try:
            pos = self.api.get_position(symbol)
            return float(pos.qty)
        except Exception:
            return 0.0

    def place_order(self, symbol, qty, side, type='limit', limit_price=None, time_in_force='day'):
        logging.info(f"ORDER {side} {qty} {symbol} @ {limit_price} ({type})")
        return self.api.submit_order(symbol=symbol, qty=qty, side=side, type=type,
                                     limit_price=limit_price, time_in_force=time_in_force)

    def close_position(self, symbol):
        try:
            self.api.close_position(symbol)
            logging.info(f"Closed position {symbol}")
        except Exception as e:
            logging.error(f"Close error {symbol}: {e}")
