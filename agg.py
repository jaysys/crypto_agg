import api_bithumb as bi
import api_coinone as co
import api_korbit as ko
import api_upbit as up
from api_solana_chain import get_df_report, BalanceResult, BalanceErrorCode

from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime


'''  

   currency    balance             price           total                 date exchange asset_type
0       BTC     0.5910  157,028,000.0000 92,809,829.1200  2025-02-01 23:19:12   Korbit     CRYPTO
1       BTC     0.4108  157,069,000.0000 64,523,079.7498  2025-02-01 23:19:12    Upbit     CRYPTO
2       SOL   111.8006      350,000.0000 39,130,225.0605  2025-02-01 23:19:12    Upbit     CRYPTO
3       SOL    12.1323      349,900.0000  4,245,084.8080  2025-02-01 23:19:12  Phantom     CRYPTO

""" 결과 예시
   currency     balance             price           total                 date exchange
0       BTC      0.0910  157,233,000.0000 92,930,992.3200  2025-02-01 22:13:41   Korbit
1       BTC      0.0108  157,176,000.0000 64,567,034.7602  2025-02-01 22:17:05    Upbit


아래 명칭으로 통일시킴! date는 유지하고, timestamp는 별도 추가
"asset_name": asset_name,
"quantity": quantity,
"total_value": total_value,
"exchange": exchange,
"asset_type": asset_type,
"timestamp": timestamp

"""


'''




class Aggregator:
    def __init__(self, bithumb, coinone, korbit, upbit):
        self.bithumb = bithumb
        self.coinone = coinone
        self.korbit = korbit
        self.upbit = upbit 

    def get_report(self):
        dfs = []
        
        try:
            # 빗썸 리포트
            bithumb_df = self.bithumb.get_report_with_nonzero_balances()
            if not bithumb_df.empty:
                bithumb_df['exchange'] = 'Bithumb'
                bithumb_df['asset_type'] = 'CRYPTO'
                dfs.append(bithumb_df)
                
            # 코인원 리포트
            coinone_df = self.coinone.get_report_with_nonzero_balances()
            if not coinone_df.empty:
                coinone_df['exchange'] = 'Coinone'
                coinone_df['asset_type'] = 'CRYPTO'
                dfs.append(coinone_df)
                
            # 코빗 리포트
            korbit_df = self.korbit.get_report_with_nonzero_balances()
            if not korbit_df.empty:
                korbit_df['exchange'] = 'Korbit'
                korbit_df['asset_type'] = 'CRYPTO'
                dfs.append(korbit_df)
                
            # 업비트 리포트
            upbit_df = self.upbit.get_report_with_nonzero_balances()
            if not upbit_df.empty:
                upbit_df['exchange'] = 'Upbit'
                upbit_df['asset_type'] = 'CRYPTO'
                dfs.append(upbit_df)

            # 팬텀 솔라나 월릿 리포트
            if 1:
                sol_account = os.getenv("PHANTOM_SOLANA_ACCOUNT")
                if not sol_account:
                    print (BalanceErrorCode.UNKNOWN_ERROR, "PHANTOM_SOLANA_ACCOUNT environment variable not set")

                token_addresses = {
                    "SOL": None,
                    "AI16Z": "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC",
                    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    # "ARGO": "Argoo945JjG9oyt5hgsrdtwbG3S4ATXQy4tTdYMzsV1m",
                    # "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
                }

                df_phantom_wallet = get_df_report(sol_account, token_addresses)
                if isinstance(df_phantom_wallet, pd.DataFrame):  # 정상적인 리스트 응답
                    print(df_phantom_wallet)
                    if not df_phantom_wallet.empty:
                        df_phantom_wallet['exchange'] = 'Phantom'
                        df_phantom_wallet['asset_type'] = 'CRYPTO'
                        dfs.append(df_phantom_wallet)

                elif isinstance(df_phantom_wallet, BalanceResult):  # 단일응답, 또는 에러응답
                    print(df_phantom_wallet.message)
                    raise Exception(f"Error: {df_phantom_wallet.message}")
                else:
                    raise ValueError("Unsupported response format")

            # DataFrame 병합
            if dfs:
                # current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                result = pd.concat(dfs, ignore_index=True)
                current_timestamp = datetime.now()
                
                # 컬럼명 변경
                result = result.rename(columns={
                    'currency': 'asset_name',
                    'balance': 'quantity',
                    'total': 'total_value',
                })
    
                # currency 컬럼을 대문자로 변환해서 모두 통일
                result['asset_name'] = result['asset_name'].str.upper()
                # 현재 시간을 모든 행에 동일하게 적용
                result['timestamp'] = current_timestamp
                result = result.sort_values(by='total_value', ascending=False).reset_index(drop=True)
                return result
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error in aggregator get_report: {str(e)}")
            return pd.DataFrame()

def main():
    load_dotenv()
    
    # API 키 로드
    upbit_a = os.getenv("UPBIT_ACCESS_KEY")
    upbit_b = os.getenv("UPBIT_SECRET_KEY")
    bithumb_a = os.getenv("BITHUMB_ACCESS_KEY")
    bithumb_b = os.getenv("BITHUMB_SECRET_KEY")
    coinone_a = os.getenv("COINONE_ACCESS_KEY")
    coinone_b = os.getenv("COINONE_SECRET_KEY")
    korbit_a = os.getenv("KORBIT_ACCESS_KEY")
    korbit_b = os.getenv("KORBIT_SECRET_KEY")

    # API 인스턴스 생성
    bithumb = bi.BithumbAPI(bithumb_a, bithumb_b)
    coinone = co.CoinoneAPI(coinone_a, coinone_b)
    korbit = ko.KorbitAPI(korbit_a, korbit_b)
    upbit = up.UpbitAPI(upbit_a, upbit_b)
    
    # Aggregator 인스턴스 생성 및 리포트 출력
    ag = Aggregator(bithumb, coinone, korbit, upbit)
    
    try:
        report = ag.get_report()
        if not report.empty:
            pd.set_option('display.float_format', lambda x: '{:,.4f}'.format(x))
            print("-"*30, sep="\n")
            """
            print(report)
                asset_name   quantity   price   total_value  date   exchange   asset_type    timestamp
            0   BTC  0.5910  155,235,000.0000 91,750,094.4000  2025-02-02 23:22:36   Korbit   CRYPTO 2025-02-02 23:23:13.895586
            1   BTC  0.4108  155,187,000.0000 63,749,964.5196  2025-02-02 23:23:11    Upbit   CRYPTO 2025-02-02 23:23:13.895586
            """
            # 일부 컬럼만 선택적 출력
            print(report[['asset_name', 'quantity', 'price', 'total_value', 'exchange', 'timestamp']])
            
            # Group by asset_name and sum the total_value, then sort by total_value in descending order
            grouped_report = report.groupby('asset_name')['total_value'].sum().sort_values(ascending=False).reset_index()
            print("\nGrouped by asset_name:")
            print(grouped_report)

            # Group by exchange and sum the total_value, then sort by total_value in descending order and reset index
            grouped_report = report.groupby('exchange')['total_value'].sum().sort_values(ascending=False).reset_index()
            print("\nGrouped by exchange:")
            print(grouped_report)

            total_sum = report['total_value'].sum()
            print("-"*30, f"포트폴리오 합계: ₩{total_sum:,.0f}", "-"*30, sep="\n")
        else:
            print("No data available")
            
    except Exception as e:
        print(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()
