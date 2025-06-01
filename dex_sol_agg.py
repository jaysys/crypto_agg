import os
import sys
import pandas as pd
from dotenv import load_dotenv
from services.solana_chain_api import get_df_report, BalanceResult, BalanceErrorCode

def main():
    # Load environment variables
    load_dotenv()
    sol_account = os.getenv("PHANTOM_SOLANA_ACCOUNT")
    if not sol_account:
        print("Error: PHANTOM_SOLANA_ACCOUNT environment variable not set")
        print("Please create a .env file with your Phantom wallet address:")
        print("PHANTOM_SOLANA_ACCOUNT=your_phantom_wallet_address_here")
        sys.exit(1)

    # Define token addresses to track
    token_addresses = {
        "SOL": None,  # Native SOL doesn't need a token address
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
        # Add more tokens as needed: "TOKEN_SYMBOL": "TOKEN_ADDRESS"
    }

    print(f"Fetching balances for Solana account: {sol_account[:4]}...{sol_account[-4:]}")
    print("This may take a moment as we connect to the Solana network...\n")
    
    try:
        df = get_df_report(sol_account, token_addresses)
        
        if isinstance(df, pd.DataFrame):
            if df.empty:
                print("No token balances found for this wallet address.")
            else:
                # Format the output
                pd.set_option('display.float_format', lambda x: '{:,.4f}'.format(x) if abs(x) < 1000000 else '{:,.0f}'.format(x))
                print("-" * 80)
                print("SOLANA WALLET BALANCES")
                print("-" * 80)
                print(df[['currency', 'balance', 'price', 'total']].to_string(index=False))
                print("-" * 80)
                total_value = df['total'].sum()
                print(f"TOTAL VALUE: ₩{total_value:,.2f}")
                print("-" * 80)
        elif isinstance(df, BalanceResult):
            print(f"Error: {df.message}")
            if df.code == BalanceErrorCode.RATE_LIMIT_EXCEEDED:
                print("Please try again later or use a different RPC endpoint.")
            sys.exit(1)
        else:
            print("Error: Unexpected response format from Solana API")
            sys.exit(1)
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Please check your internet connection and try again.")
        sys.exit(1)

"""
  currency       balance   price         total                 date
0      SOL     12.132280  1000.0  1.213228e+04  2025-02-01 21:48:48
1     USDC     25.281683  1000.0  2.528168e+04  2025-02-01 21:48:48
"""
main()


