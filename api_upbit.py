import os
from dotenv import load_dotenv
import requests
import jwt
import uuid
import hashlib
from urllib.parse import urlencode
import pprint as pp
import pandas as pd
from datetime import datetime

class UpbitAPI:
    BASE_URL = "https://api.upbit.com/v1/"

    def __init__(self, access_key, secret_key):
        self.access_key = access_key
        self.secret_key = secret_key

    def _get_auth_token(self, query=None):
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }
        
        if query:
            query_string = urlencode(query).encode()
            m = hashlib.sha512()
            m.update(query_string)
            query_hash = m.hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'

        jwt_token = jwt.encode(payload, self.secret_key)
        if isinstance(jwt_token, bytes):
            jwt_token = jwt_token.decode('utf-8')
        return f'Bearer {jwt_token}'

    def get_balances(self, currencies=None):
        endpoint = "accounts"
        headers = {'Authorization': self._get_auth_token()}
        response = requests.get(self.BASE_URL + endpoint, headers=headers)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return []
            
        balances = response.json()
        for balance in balances:
            balance['balance'] = str(float(balance['balance']) + float(balance['locked']))
        
        if currencies:
            return [balance for balance in balances if balance['currency'] in currencies]
        return balances

    def get_balance_by_currency(self, currency):
        balances = self.get_balances([currency])
        return balances[0] if balances else None

    def get_nonzero_balances(self):
        # 제외할 코인 리스트 - 가격 정보 제공안함
        EXCLUDED_COINS = ['ETHW', 'ETHF']
        
        balances = self.get_balances()
        return [
            balance for balance in balances 
            if float(balance['balance']) > 0 and balance['currency'].upper() not in EXCLUDED_COINS
        ]


    def get_price_by_currency(self, coin: str):
        if coin == 'KRW':
            return 1, datetime.now()
            
        endpoint = f"ticker?markets=KRW-{coin}"
        try:
            response = requests.get(self.BASE_URL + endpoint)
            response.raise_for_status()
            data = response.json()
            if data:
                timestamp = datetime.fromtimestamp(data[0]['timestamp'] / 1000)
                return data[0]['trade_price'], timestamp
            return None, None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching price for {coin}: {e}")
            return None, None

    def get_report(self, currencies):
        report = []
        for currency in currencies:
            balance = self.get_balance_by_currency(currency)
            if balance:
                price, timestamp = self.get_price_by_currency(currency)
                if price is not None:
                    total = float(balance['balance']) * price
                    report.append({
                        'currency': currency,
                        'balance': float(balance['balance']),
                        'price': price,
                        'total': total,
                        'date': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    })

        df = pd.DataFrame(report)
        df = df.sort_values(by="total", ascending=False, ignore_index=True)
        return df
    

    def get_report_with_nonzero_balances(self):
        nonzero_balances = self.get_nonzero_balances()
        nonzero_currencies = [item['currency'] for item in nonzero_balances]
        return self.get_report(nonzero_currencies)


def usage_example():
    load_dotenv()

    ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
    SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")

    if not ACCESS_KEY or not SECRET_KEY:
        print("Error: Please set UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY in .env file")
        return

    api = UpbitAPI(ACCESS_KEY, SECRET_KEY)

    print(f"Upbit Portfolio Report ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    
    try:
        nonzero_balances = api.get_nonzero_balances()
        nonzero_currencies = [item['currency'] for item in nonzero_balances]
        
        print(f"보유 중인 코인: {len(nonzero_currencies)}개")
        print(f"코인 목록: {', '.join(nonzero_currencies)}")

        report_df = api.get_report(nonzero_currencies)
        if not report_df.empty:
            # 컬럼 순서 지정
            columns = ['currency', 'balance', 'price', 'total', 'date']
            df = report_df[columns].sort_values(by="total", ascending=False)
            
            # DataFrame 포맷팅
            pd.set_option('display.float_format', lambda x: '{:,.4f}'.format(x))
            print(df)
            
            total_sum = df['total'].sum()
            print(f"업비트 합계: {total_sum:,.0f}(원)")
        else:
            print("No assets found or error occurred while fetching data")

    except Exception as e:
        print(f"Error generating report: {e}")

if __name__ == "__main__":
    usage_example()