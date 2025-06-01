import os
import requests
import json
from dotenv import load_dotenv
import pprint as pp
import pandas as pd
from datetime import datetime
import hmac
import hashlib
import time

class KorbitAPI:
    BASE_URL = "https://api.korbit.co.kr"

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = 0
        self._get_access_token()

    def _get_access_token(self):
        if time.time() < self.token_expires_at:
            return

        url = f"{self.BASE_URL}/v1/oauth2/access_token"
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expires_at = time.time() + token_data['expires_in'] - 60
        except Exception as e:
            print(f"Error getting access token: {e}")
            raise

    def _get_headers(self):
        self._get_access_token()  # Refresh token if needed
        return {
            'Authorization': f'Bearer {self.access_token}'
        }

    def get_balances(self, currencies=None):
        endpoint = f"{self.BASE_URL}/v1/user/balances"
        try:
            response = requests.get(endpoint, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()
            
            # Debug print to see the actual response structure
            # print("Debug - API Response:", json.dumps(data, indent=2))
            
            if not data:
                return {}
                
            balances = {}
            for currency, balance in data.items():
                if currencies and currency not in currencies:
                    continue
                # 응답 구조에 따라 키 이름을 동적으로 처리
                available = float(balance.get('available', 0))
                trade_in_use = float(balance.get('trade_in_use', 0))  # 'locked' 또는 다른 키일 수 있음
                
                balances[currency] = {
                    'currency': currency,
                    'balance': available + trade_in_use,
                    'available': available,
                    'locked': trade_in_use
                }
            return balances
        except requests.exceptions.RequestException as e:
            print(f"Error fetching balances: {e}")
            return {}

    def get_balance_by_currency(self, currency):
        balances = self.get_balances([currency])
        return balances.get(currency)

    def get_nonzero_balances(self):
        # 제외할 코인 리스트 - 가격 정보 제공안함
        EXCLUDED_COINS = ['ethw', 'ethf']
        
        balances = self.get_balances()
        return {
            currency: data 
            for currency, data in balances.items() 
            if data['balance'] > 0 and currency.lower() not in EXCLUDED_COINS
        }

    def get_price_by_currency(self, coin: str):
        if coin.upper() == 'KRW':
            return 1, datetime.now()
            
        endpoint = f"{self.BASE_URL}/v1/ticker/detailed"
        params = {'currency_pair': f"{coin.lower()}_krw"}
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            timestamp = datetime.fromtimestamp(int(data['timestamp'])/1000)
            return float(data['last']), timestamp
        except requests.exceptions.RequestException as e:
            print(f"Error fetching price for {coin}: {e}")
            return None, None

    def get_report(self, currencies):
            # 제외할 코인 리스트
            EXCLUDED_COINS = ['ethw', 'ethf']
            
            report = []
            balances = self.get_balances(currencies)
            
            for currency, balance_data in balances.items():
                # 제외할 코인 스킵
                if currency.lower() in EXCLUDED_COINS:
                    continue
                    
                price, timestamp = self.get_price_by_currency(currency)
                if price is not None:
                    available = balance_data['available']
                    locked = balance_data['locked']
                    total = (available + locked) * price
                    report.append({
                        'currency': currency,
                        'balance': available + locked,
                        'price': price,
                        'total': total,
                        'date': timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            df = pd.DataFrame(report)
            if not df.empty:
                columns = ['currency', 'balance', 'price', 'total', 'date']
                df = df[columns].sort_values(by="total", ascending=False)
                
                pd.set_option('display.float_format', lambda x: f'{x:,.4f}')
                df['price'] = df['price'].apply(lambda x: f'{x:,.4f}')
                df['total'] = df['total'].apply(lambda x: f'{x:,.4f}')

                # Remove formatting for calculation
                df['total'] = df['total'].str.replace(',', '').astype(float)

            df = df.sort_values(by="total", ascending=False, ignore_index=True)
            return df
    
    def get_report_with_nonzero_balances(self):
        nonzero_balances = self.get_nonzero_balances()
        nonzero_currencies = list(nonzero_balances.keys())
        return self.get_report(nonzero_currencies)

def sample_usage():
    load_dotenv()

    CLIENT_ID = os.getenv("KORBIT_ACCESS_KEY")
    CLIENT_SECRET = os.getenv("KORBIT_SECRET_KEY")

    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: Please set KORBIT_CLIENT_ID and KORBIT_CLIENT_SECRET in .env file")
        return

    api = KorbitAPI(CLIENT_ID, CLIENT_SECRET)

    # btc_balance = api.get_balance_by_currency('btc')
    # print("btc: ", btc_balance)
    # import pprint as pp
    # pp.pprint(api.get_balances(['btc', 'eth', 'xrp', 'krw']))
    # pp.pprint(api.get_nonzero_balances())
    # print(api.get_price_by_currency('btc'))

    print(f"Korbit Portfolio Report ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    
    try:
        nonzero_balances = api.get_nonzero_balances()
        nonzero_currencies = list(nonzero_balances.keys())
        
        print(f"보유 중인 코인: {len(nonzero_currencies)}개")
        print(f"코인 목록: {', '.join(nonzero_currencies)}")

        report_df = api.get_report(nonzero_currencies)
        if not report_df.empty:
            print(report_df)
            total_sum = report_df['total'].astype(float).sum()
            print(f"코빗 합계: {total_sum:,.2f} KRW")
        else:
            print("No assets found or error occurred while fetching data")

    except Exception as e:
        print(f"Error generating report: {e}")


if __name__ == "__main__":
    sample_usage()