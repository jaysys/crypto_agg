import os
import pandas as pd
from dotenv import load_dotenv
from services.solana_chain_api import get_df_report, BalanceResult, BalanceErrorCode

def main():
    load_dotenv()
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

    df = get_df_report(sol_account, token_addresses)
    if isinstance(df, pd.DataFrame):  # 정상적인 리스트 응답
        print(df)
    elif isinstance(df, BalanceResult):  # 단일응답, 또는 에러응답
        print(df.message)
        raise Exception(f"Error: {df.message}")
    else:
        raise ValueError("Unsupported response format")

"""
  currency       balance   price         total                 date
0      SOL     12.132280  1000.0  1.213228e+04  2025-02-01 21:48:48
1     USDC     25.281683  1000.0  2.528168e+04  2025-02-01 21:48:48
"""
main()


