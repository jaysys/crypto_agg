from typing import Union, Dict, Tuple
from dataclasses import dataclass
import requests

@dataclass
class ExchangePrice:
    exchange: str
    price: float
    error: str = None

    @property
    def is_error(self) -> bool:
        return self.error is not None

class PriceAPI:
    def __init__(self):
        self.token_map = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "sol": "solana",
            "xrp": "ripple",
            "ada": "cardano",
            "doge": "dogecoin",
            "link": "chainlink",
            "uni": "uniswap",
            "ai16z": "ai16z",
            "virtual": "virtual-protocol",
            "sui": "sui",
            "fet": "fetch-ai",
            "usdc": "usd-coin",
            "usdt": "tether",
        }

    def _make_request(self, url: str) -> Union[Dict, str]:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return f"Error: {str(e)}"

    def get_upbit_price(self, coin: str) -> ExchangePrice:
        if coin.lower() == 'krw':
            return ExchangePrice("Upbit", 1.0)

        url = f'https://api.upbit.com/v1/ticker?markets=KRW-{coin.upper()}'
        data = self._make_request(url)

        if isinstance(data, str):
            return ExchangePrice("Upbit", 0.0, data)

        if data and len(data) > 0:
            try:
                return ExchangePrice("Upbit", float(data[0].get("trade_price", 0)))
            except (ValueError, TypeError):
                return ExchangePrice("Upbit", 0.0, "Error: Invalid price data")
        return ExchangePrice("Upbit", 0.0, "Error: Empty response from API")

    def get_bithumb_price(self, coin: str) -> ExchangePrice:
        if coin.lower() == 'krw':
            return ExchangePrice("Bithumb", 1.0)

        url = f'https://api.bithumb.com/public/ticker/{coin}_KRW'
        data = self._make_request(url)

        if isinstance(data, str):
            return ExchangePrice("Bithumb", 0.0, data)

        if data.get("status") == "0000":
            try:
                return ExchangePrice("Bithumb", float(data["data"].get("closing_price", 0)))
            except (ValueError, TypeError):
                return ExchangePrice("Bithumb", 0.0, "Error: Invalid price data")
        return ExchangePrice("Bithumb", 0.0, f"Error: API returned status {data.get('status')}")

    def get_coinone_price(self, coin: str) -> ExchangePrice:
        if coin.lower() == 'krw':
            return ExchangePrice("Coinone", 1.0)

        url = f'https://api.coinone.co.kr/ticker/?currency={coin}'
        data = self._make_request(url)

        if isinstance(data, str):
            return ExchangePrice("Coinone", 0.0, data)

        if data.get("errorCode") == "0":
            try:
                return ExchangePrice("Coinone", float(data.get("last", 0)))
            except (ValueError, TypeError):
                return ExchangePrice("Coinone", 0.0, "Error: Invalid price data")
        return ExchangePrice("Coinone", 0.0, f"Error: API returned errorCode {data.get('errorCode')}")

    def get_coingecko_price(self, coin: str) -> ExchangePrice:
        if coin.lower() == 'krw':
            return ExchangePrice("Coingecko", 1.0)

        token_id = self.token_map.get(coin.lower(), coin.lower())
        url = f'https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=krw'
        data = self._make_request(url)

        if isinstance(data, str):
            return ExchangePrice("Coingecko", 0.0, data)

        try:
            price = data.get(token_id, {}).get('krw', 0)
            return ExchangePrice("Coingecko", float(price))
        except (ValueError, TypeError):
            return ExchangePrice("Coingecko", 0.0, f"Error: Unable to get price for {coin}")
        
    def get_first_valid_price(self, symbol: str) -> Tuple[float, str]:
        """Get the first valid price from exchanges in priority order"""
        exchanges = [
            (self.get_upbit_price, "Upbit"),
            (self.get_bithumb_price, "Bithumb"),
            (self.get_coinone_price, "Coinone"),
            (self.get_coingecko_price, "Coingecko")
        ]

        for get_price, exchange_name in exchanges:
            result = get_price(symbol)
            if not result.is_error and float(result.price) > 0:
                return float(result.price), exchange_name

        return 0.0, "No valid price found"


def sample_usage():
    price = PriceAPI()
    print("virtual", price.get_first_valid_price('virtual'))
    print("ai16z", price.get_first_valid_price('ai16z'))
    print("fet", price.get_first_valid_price('fet'))
    print("btc", price.get_first_valid_price('btc'))
    print("argo", price.get_first_valid_price('argo'))
    print("notdefinedcointhing", price.get_first_valid_price('notdefinedcointhing'))

    print()
    btc_price, btc_exchange = price.get_first_valid_price('btc')
    print(f"BTC price: {btc_price} from {btc_exchange}")
    ai16z_price, ai16z_exchange = price.get_first_valid_price('ai16z')
    print(f"ai16z price: {ai16z_price} from {ai16z_exchange}")
    fet_price, fet_exchange = price.get_first_valid_price('fet')
    print(f"FET price: {fet_price} from {fet_exchange}")
    argo_price, argo_exchange = price.get_first_valid_price('argo')
    print(f"ARGO price: {argo_price} from {argo_exchange}")
    


if __name__ == "__main__":
    sample_usage()

 