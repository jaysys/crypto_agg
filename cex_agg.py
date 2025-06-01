from services import bithumb_api as bi
from services import coinone_api as co
from services import korbit_api as ko
from services import upbit_api as up
from dotenv import load_dotenv
import os
import pandas as pd

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
                dfs.append(bithumb_df)
                
            # 코인원 리포트
            coinone_df = self.coinone.get_report_with_nonzero_balances()
            if not coinone_df.empty:
                coinone_df['exchange'] = 'Coinone'
                dfs.append(coinone_df)
                
            # 코빗 리포트
            korbit_df = self.korbit.get_report_with_nonzero_balances()
            if not korbit_df.empty:
                korbit_df['exchange'] = 'Korbit'
                dfs.append(korbit_df)
                
            # 업비트 리포트
            upbit_df = self.upbit.get_report_with_nonzero_balances()
            if not upbit_df.empty:
                upbit_df['exchange'] = 'Upbit'
                dfs.append(upbit_df)
            
            # DataFrame 병합
            if dfs:
                result = pd.concat(dfs, ignore_index=True)
                result = result.sort_values(by='total', ascending=False).reset_index(drop=True)
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
            print(report)
            total_sum = report['total'].sum()
            print("-"*30, f"포트폴리오 합계: ₩{total_sum:,.0f}", "-"*30, sep="\n")
        else:
            print("No data available")
    except Exception as e:
        print(f"Error in main: {str(e)}")







if __name__ == "__main__":
    main()