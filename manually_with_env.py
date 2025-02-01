"""
.env 파일에 저장된 보유 코인 정보를 읽어와서 각 코인의 현재 가격을 계산하여 포트폴리오를 출력합니다. 
    [.env]파일 예시:
    # 보유수량
    CRYPTO_BTC=1.001830
    CRYPTO_SOL=123.852
    
sample_usage:
함수를 호출하면, .env 파일에 저장된 보유 코인 정보를 읽어와서 각 코인의 현재 가격을 계산하여 포트폴리오를 출력합니다.
    portfolio_manager = PortfolioManager()
    portfolio_df = portfolio_manager.calculate_portfolio()
    print(portfolio_df)
"""

import os
from typing import List
from dataclasses import dataclass
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

import api_prices as prices 

@dataclass
class CryptoHolding:
    symbol: str
    amount: float

class PortfolioManager:
    def __init__(self):
        self.api = prices.PriceAPI()
        self.holdings: List[CryptoHolding] = []
        self.load_holdings()


    def load_holdings(self):
        """Load holdings from .env file"""
        load_dotenv()
        
        self.holdings = []
        
        for key, value in os.environ.items():
            if key.startswith('CRYPTO_'):
                symbol = key.split('_')[1].lower()
                try:
                    amount = float(value)
                    self.holdings.append(CryptoHolding(symbol, amount))
                except ValueError:
                    print(f"Warning: Invalid amount for {symbol}: {value}")

    def calculate_portfolio(self) -> pd.DataFrame:
        """Calculate portfolio values and return as DataFrame"""
        portfolio_data = []
        total_value = 0.0
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for holding in self.holdings:
            price, exchange = self.api.get_first_valid_price(holding.symbol)
            total_holding_value = price * holding.amount
            total_value += total_holding_value

            portfolio_data.append({
                "date": current_time,
                "symbol": holding.symbol.upper(),
                "amount": holding.amount,
                "price_krw": price,
                "exchange": exchange,
                "total_krw": total_holding_value
            })

        # Create DataFrame without total row
        df = pd.DataFrame(portfolio_data)

        # 'Total Value (KRW)' 기준 내림차순 정렬 + 인덱스 초기화
        df = df.sort_values(by="total_krw", ascending=False).reset_index(drop=True)

        # Add total row after sorting
        total_row = pd.DataFrame([{
            "date": current_time,
            "symbol": "TOTAL",
            "amount": pd.NA,
            "price_krw": pd.NA,
            "exchange": pd.NA,
            "total_krw": total_value
        }])

        # Concatenate sorted data with total row
        df = pd.concat([df, total_row], ignore_index=True)
        
        # Ensure correct column order
        columns = ["date", "symbol", "amount", "price_krw", "exchange", "total_krw"]
        df = df[columns]
        
        return df

def sample_usage():
    print("나의 포트폴리오 상태 리포트", "-"*30, sep="\n")
    portfolio_manager = PortfolioManager()
    portfolio_df = portfolio_manager.calculate_portfolio()
    pd.options.display.float_format = '{:,.2f}'.format
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(portfolio_df)


if __name__ == "__main__":
    sample_usage()

 