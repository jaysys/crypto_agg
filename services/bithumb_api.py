import os
import jwt
import uuid
import time
import requests
import pandas as pd
from datetime import datetime
import pprint as pp
from typing import List, Dict, Union
from dotenv import load_dotenv

class BithumbAPI:
    BASE_URL = "https://api.bithumb.com"

    def __init__(self, access_token: str, secret_key: str):
        self.access_token = access_token
        self.secret_key = secret_key

    def _get_jwt_token(self) -> str:
        """JWT 토큰 생성"""
        payload = {
            'access_key': self.access_token,
            'nonce': str(uuid.uuid4()),
            'timestamp': round(time.time() * 1000)
        }
        jwt_token = jwt.encode(payload, self.secret_key)
        return f'Bearer {jwt_token}'

    def _request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """API 요청 처리"""
        try:
            url = f"{self.BASE_URL}{endpoint}"
            headers = {'Authorization': self._get_jwt_token()}

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params)
            else:
                response = requests.post(url, headers=headers, json=params)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return []

    def get_balances(self, currencies: List[str] = None) -> List[Dict]:
        """
        계좌 잔고 조회
        Response structure:
        {
            'currency': str,            # 화폐 종류
            'balance': str,             # 잔고 수량
            'locked': str,              # 주문 중 묶여있는 수량
            'avg_buy_price': str,       # 매수 평균가
            'avg_buy_price_modified': bool,  # 매수 평균가 수정 여부
            'unit_currency': str        # 평단가 화폐
        }
        """
        response = self._request('GET', '/v1/accounts')
        # print("response: ")
        # pp.pprint(response)

        accounts = [{'currency': account['currency'], 'balance': float(account['balance']) + float(account['locked'])} for account in response]

        if currencies is None: # 별도 코인 목록이 없는 경우 -> 빗썸이 응답해주는 계좌잔고조회 구조형태 그대로 리턴해준다. (잔고가 있는 것만 리턴된다.)
            return accounts

        result = []
        for currency in currencies: # 요청받은 코인목록 파라미터가 있는 경우 -> 해당 코인이 회신받은 코인목록에 있는 경우는 그대로, 없는 경우에는 0으로 채워서 리턴해준다.
            account = next((acc for acc in accounts if acc['currency'] == currency), None)
            if account:
                result.append(account)
            else:
                result.append({'currency': currency, 'balance': 0.0})
        
        return result

    def get_balance_by_currency(self, currency: str) -> Dict:
        """단일 화폐 잔액 조회"""
        accounts = self.get_balances([currency])
        if accounts and float(accounts[0]['balance']) > 0:
            return accounts[0]
        else: # 잔고가 없는 경우
            return {
                'currency': currency,
                'balance': '0'
            }

    def get_nonzero_balances(self) -> List[Dict]:
        """잔액이 있는 화폐만 조회, 특정 코인 목록에 넣으면 제외"""
        EXCLUDED_COINS = ['P', 'ETHW', 'ETHF']
        
        balances = self.get_balances()
        return [
            balance for balance in balances 
            if float(balance['balance']) > 0 and balance['currency'].upper() not in EXCLUDED_COINS
        ]

    def get_price_by_currency(self, coin: str) -> float:
        """현재가 조회"""
        try:
            response = self._request('GET', f'/public/ticker/{coin}_KRW')
            if isinstance(response, dict) and response.get('data'):
                return float(response['data']['closing_price'])
            return 0.0
        except (ValueError, KeyError) as e:
            print(f"Error getting price for {coin}: {e}")
            return 0.0


    def get_report(self, currencies: List[str] = None) -> pd.DataFrame:
        """보유 화폐 리포트 생성"""
        accounts = self.get_balances(currencies)
        if not accounts:
            return pd.DataFrame(columns=['currency', 'balance', 'price', 'total', 'date'])
            
        report_data = []
        for account in accounts:
            currency = account['currency']
            balance = float(account['balance'])
            
            if currency == 'KRW':
                price = 1.0
            else:
                price = self.get_price_by_currency(currency)
            
            report_data.append({
                'currency': currency,
                'balance': balance,
                'price': price,
                'total': (balance) * price,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
        return pd.DataFrame(report_data)

    def get_report_with_nonzero_balances(self) -> pd.DataFrame:
        """잔액이 있는 화폐에 대한 리포트 생성"""
        nonzero_accounts = self.get_nonzero_balances()
        nonzero_currencies = [account['currency'] for account in nonzero_accounts]
        return self.get_report(nonzero_currencies)
    
def usage_example():
    load_dotenv()
    
    ACCESS_KEY = os.getenv("BITHUMB_ACCESS_KEY")
    SECRET_KEY = os.getenv("BITHUMB_SECRET_KEY")
    
    if not ACCESS_KEY or not SECRET_KEY:
        print("Error: Please set BITHUMB_ACCESS_KEY and BITHUMB_SECRET_KEY in your .env file")
        exit(1)
    
    api = BithumbAPI(ACCESS_KEY, SECRET_KEY)
    
    if 1:
        nonzero_accounts = api.get_nonzero_balances()
        nonzero_currencies = [account['currency'] for account in nonzero_accounts]
        print(f"빗썸거래소에는 총{len(nonzero_currencies)}개 코인이 있습니다. {nonzero_currencies}")
        
        # Generate report
        pd.set_option('display.float_format', lambda x: '{:,.4f}'.format(x))
        report_df = api.get_report(nonzero_currencies)
        
        if not report_df.empty:
            df = report_df.sort_values(by="total", ascending=False).reset_index(drop=True)
            print(df)
            total_sum = df['total'].sum()
            print(f"빗썸 합계: {total_sum:,.0f}(원)")
        else:
            print("No balance data available")

if __name__ == "__main__":
    usage_example()