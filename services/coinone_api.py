import os
import hmac
import json
import uuid
import base64
import hashlib
import requests
import pprint as pp
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

class CoinoneAPI:
    BASE_URL = "https://api.coinone.co.kr/"

    def __init__(self, access_token, secret_key):
        self.access_token = access_token
        self.secret_key = bytes(secret_key, 'utf-8')

    def _get_encoded_payload(self, payload):
        payload['nonce'] = str(uuid.uuid4())
        encoded_json = base64.b64encode(json.dumps(payload).encode('utf-8'))
        return encoded_json

    def _get_signature(self, encoded_payload):
        signature = hmac.new(self.secret_key, encoded_payload, hashlib.sha512)
        return signature.hexdigest()

    def _post_request(self, endpoint, payload):
        url = f"{self.BASE_URL}{endpoint}"
        encoded_payload = self._get_encoded_payload(payload)
        headers = {
            'Content-type': 'application/json',
            'X-COINONE-PAYLOAD': encoded_payload,
            'X-COINONE-SIGNATURE': self._get_signature(encoded_payload),
        }
        response = requests.post(url, headers=headers)
        return response.json()

    def get_balances(self, currencies):
        response = self._post_request("/v2.1/account/balance", {
            'access_token': self.access_token,
            'currencies': currencies
        })
        
        if response.get("result") != "success":
            return []
        
        return [
            {
                "currency": balance["currency"],
                "balance": float(balance["available"]) + float(balance["limit"])
            }
            for balance in response.get("balances", [])
        ]
    
    def get_balance_by_currency(self, currency):
        response = self._post_request("/v2.1/account/balance", {
            'access_token': self.access_token,
            'currencies': [currency]
        })
        
        if response.get("result") != "success":
            return None
        
        balance_data = next((balance for balance in response.get("balances", []) if balance["currency"] == currency), None)
        if balance_data:
            return {
                "currency": balance_data["currency"],
                "balance": float(balance_data["available"]) + float(balance_data["limit"])
            }
        return None
    
    def get_nonzero_balances(self):
        response = self._post_request("/v2.1/account/balance/all", {
            'access_token': self.access_token
        })
        
        if response.get("result") != "success":
            return []
        
        return [
            {
                "currency": balance["currency"],
                "balance": float(balance["available"]) + float(balance["limit"])
            }
            for balance in response.get("balances", [])
            if float(balance["available"]) + float(balance["limit"]) > 0
        ]

    def get_price_by_currency(self, coin: str):
        if coin.lower() == 'krw':
            return 1.0

        def _make_request(url: str):
            try:
                response = requests.get(url)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                return f"Error: {str(e)}"

        url = f'https://api.coinone.co.kr/ticker/?currency={coin}'
        data = _make_request(url)

        if data.get("errorCode") == "0":
            try:
                return float(data.get("last", 0))
            except (ValueError, TypeError):
                return f"Error: Invalid Coinone price data.."
        return f"Error: Invalid Coinone price data"

    def get_report(self, currencies):
        # Get balances for the requested currencies
        balances = self.get_balances(currencies)
        report_data = []

        # Get price for each currency and calculate the total value
        for balance in balances:
            currency = balance["currency"]
            balance_amount = balance["balance"]
            price = self.get_price_by_currency(currency)

            # Skip currencies with invalid price data
            if isinstance(price, str) and "Error" in price:
                continue

            total_value = price * balance_amount
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Append the data for the report
            report_data.append({
                "currency": currency,
                "balance": balance_amount,
                "price": price,
                "total": total_value,
                "date": current_time
            })

        # Create DataFrame and return
        df = pd.DataFrame(report_data)
        df = df.sort_values(by="total", ascending=False, ignore_index=True)
        return df
    
    
    def get_report_with_nonzero_balances(self):
        # Get non-zero balances
        nonzero_balances = self.get_nonzero_balances()
        report_data = []

        # Get price for each currency and calculate the total value
        for balance in nonzero_balances:
            currency = balance["currency"]
            balance_amount = balance["balance"]
            price = self.get_price_by_currency(currency)

            # Skip currencies with invalid price data
            if isinstance(price, str) and "Error" in price:
                continue

            total_value = price * balance_amount
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Append the data for the report
            report_data.append({
                "currency": currency,
                "balance": balance_amount,
                "price": price,
                "total": total_value,
                "date": current_time
            })

        # Create DataFrame and return
        df = pd.DataFrame(report_data)
        df = df.sort_values(by="total", ascending=False, ignore_index=True)
        return df
    


def usage_example():

    load_dotenv()
    
    ACCESS_KEY = os.getenv("COINONE_ACCESS_KEY")
    SECRET_KEY = os.getenv("COINONE_SECRET_KEY")

    api = CoinoneAPI(ACCESS_KEY, SECRET_KEY)

    if 0: # Test the API
        coin_price = api.get_price_by_currency('AI16Z')
        print("ai16z: ",coin_price)

        coin_price = api.get_price_by_currency('USDC')
        print("usdc: ",coin_price)
        
        btc_balance = api.get_balance_by_currency('AI16Z')
        pp.pprint(btc_balance)
        
        balances = api.get_balances(['KRW', 'BTC', 'SOL', 'ETH', 'USDC', 'AI16Z'])
        pp.pprint(balances)

    print("Coinone에 보유하고 있는 코인들은 다음과 같습니다.")
    nonzero_balances = api.get_nonzero_balances()
    # pp.pprint(nonzero_balances)
    nonezero_currencies = [item['currency'] for item in nonzero_balances]
    print(f"총{len(nonezero_currencies)}개 입니다. {nonezero_currencies}")

    pd.set_option('display.float_format', lambda x: '{:,.4f}'.format(x))
    report_df = api.get_report(nonezero_currencies)
    df = report_df.sort_values(by="total", ascending=False)
    print(df)
    total_sum = df['total'].sum()
    print(f"코인원 합계: {total_sum:,.0f}(원)")


if __name__ == "__main__":
    usage_example()
