import os
import time
import logging
from typing import Optional, Dict, Union, Any
from dataclasses import dataclass
from enum import Enum
import requests
from dotenv import load_dotenv
from solana.rpc.api import Client
from solders.pubkey import Pubkey
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BalanceErrorCode(Enum):
    SUCCESS = 0
    RATE_LIMIT_EXCEEDED = 1
    INVALID_ADDRESS = 2
    CONNECTION_ERROR = 3
    UNKNOWN_ERROR = 4
    FORBIDDEN_ERROR = 5
    TIMEOUT_ERROR = 6
    DNS_ERROR = 7
    MAX_RETRIES_EXCEEDED = 8

@dataclass
class BalanceResult:
    code: BalanceErrorCode
    value: Optional[float] = None
    message: Optional[str] = None
    ticker: Optional[str] = None
    address: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.code == BalanceErrorCode.SUCCESS

@dataclass
class TokenBalance:
    amount: float
    decimals: int
    
    @property
    def formatted_amount(self) -> float:
        return float(self.amount) / (10 ** self.decimals)

class SolanaApiError(Exception):
    """Base exception for Solana API errors"""
    pass

class RateLimitError(SolanaApiError):
    """Raised when rate limit is exceeded"""
    pass

class ConnectionError(SolanaApiError):
    """Raised when unable to connect to RPC endpoints"""
    pass

class RpcError(SolanaApiError):
    """Raised when RPC request fails"""
    pass

class SolanaApi:
    SOL_DECIMALS = 9
    MAX_RETRIES = 3
    RETRY_DELAY = 15
    CONNECT_TIMEOUT = 10
    
    def __init__(self, account_sol: str, provider_urls: Optional[list[str]] = None):
        if not account_sol or not isinstance(account_sol, str):
            raise ValueError("Invalid Solana account string")
            
        self.account_sol = account_sol
        self.provider_urls = provider_urls or [
            "https://api.mainnet-beta.solana.com",
            "https://rpc.ankr.com/solana",
            "https://solana-api.projectserum.com",
            "https://rpc.solana.com"
        ]
        self.client = None
        self.rpc_url = None
        self._initialize_connection()

    def _classify_error(self, error: Exception) -> tuple[BalanceErrorCode, str]:
        """Classify the error type and return appropriate error code and message"""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return BalanceErrorCode.TIMEOUT_ERROR, "Connection timed out"
        elif "403" in error_str or "forbidden" in error_str:
            return BalanceErrorCode.FORBIDDEN_ERROR, "Access forbidden"
        elif "429" in error_str or "too many requests" in error_str:
            return BalanceErrorCode.RATE_LIMIT_EXCEEDED, "Rate limit exceeded"
        elif "nodename nor servname provided" in error_str:
            return BalanceErrorCode.DNS_ERROR, "DNS resolution failed"
        elif isinstance(error, ConnectionError):
            return BalanceErrorCode.CONNECTION_ERROR, str(error)
        elif isinstance(error, RateLimitError):
            return BalanceErrorCode.RATE_LIMIT_EXCEEDED, str(error)
        else:
            return BalanceErrorCode.UNKNOWN_ERROR, f"Unknown error: {str(error)}"

    def _initialize_connection(self) -> None:
        """Initialize connection to Solana RPC with retry logic"""
        last_error = None
        successful_connection = False
        
        for provider_url in self.provider_urls:
            try:
                logger.info(f"Attempting to connect to {provider_url}")
                client = Client(provider_url)
                
                # Test the connection with timeout
                response = requests.get(provider_url, timeout=self.CONNECT_TIMEOUT)
                response.raise_for_status()
                
                # Verify RPC functionality
                client.get_version()
                
                self.client = client
                self.rpc_url = provider_url
                logger.info(f"Successfully connected to {provider_url}")
                successful_connection = True
                break
                
            except Exception as e:
                error_code, error_message = self._classify_error(e)
                last_error = f"{error_code.name}: {error_message}"
                logger.error(f"Failed to connect to {provider_url}: {last_error}")
                continue

        if not successful_connection:
            raise ConnectionError(f"Failed to connect to any Solana RPC endpoint. Last error: {last_error}")

                  
    def _handle_rate_limit(self, retry_count: int) -> None:
        """Handle rate limit with exponential backoff"""
        wait_time = self.RETRY_DELAY * (2 ** retry_count)
        logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds before retry {retry_count + 1}/{self.MAX_RETRIES}")
        time.sleep(wait_time)

    def make_rpc_request(self, method: str, params: list) -> Dict[str, Any]:
        """Send JSON-RPC request with enhanced rate limit handling"""
        if not self.client or not self.rpc_url:
            raise ConnectionError("No active RPC connection")
            
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SolanaBalanceChecker/1.0"
        }
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        for retry in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    self.rpc_url,
                    headers=headers,
                    json=payload,
                    timeout=self.CONNECT_TIMEOUT
                )
                
                if response.status_code == 429:
                    if retry < self.MAX_RETRIES - 1:
                        self._handle_rate_limit(retry)
                        continue
                    raise RateLimitError("Rate limit exceeded after all retries")
                    
                response.raise_for_status()
                data = response.json()
                
                if 'error' in data:
                    error_msg = data['error'].get('message', 'Unknown RPC error')
                    if 'Too many requests' in error_msg:
                        if retry < self.MAX_RETRIES - 1:
                            self._handle_rate_limit(retry)
                            continue
                        raise RateLimitError("Rate limit exceeded after all retries")
                    raise RpcError(f"RPC error: {error_msg}")
                    
                return data
                
            except requests.exceptions.RequestException as e:
                error_code, error_message = self._classify_error(e)
                logger.error(f"Request failed: {error_code.name} - {error_message}")
                
                if error_code == BalanceErrorCode.RATE_LIMIT_EXCEEDED and retry < self.MAX_RETRIES - 1:
                    self._handle_rate_limit(retry)
                    continue
                raise RpcError(f"RPC request failed: {error_message}")
            
        raise RateLimitError("Rate limit exceeded after all retries")

    def get_wallet_balance(self, token_address: Optional[str] = None) -> BalanceResult:
        """Get wallet balance for SOL or specified token with error handling"""
        try:
            wallet_pubkey = Pubkey.from_string(self.account_sol)
            
            if token_address:
                return self._get_token_balance(wallet_pubkey, token_address)
            return self._get_sol_balance(wallet_pubkey)
            
        except ValueError:
            return BalanceResult(
                code=BalanceErrorCode.INVALID_ADDRESS,
                message="Invalid wallet address format"
            )
        except RateLimitError as e:
            return BalanceResult(
                code=BalanceErrorCode.RATE_LIMIT_EXCEEDED,
                message=str(e)
            )
        except ConnectionError as e:
            return BalanceResult(
                code=BalanceErrorCode.CONNECTION_ERROR,
                message=str(e)
            )
        except Exception as e:
            error_code, error_message = self._classify_error(e)
            return BalanceResult(
                code=error_code,
                message=error_message
            )

    def _get_token_balance(self, wallet_pubkey: Pubkey, token_address: str) -> BalanceResult:
        """Get specified token balance with error handling"""
        try:
            response = self.make_rpc_request(
                "getTokenAccountsByOwner",
                [
                    str(wallet_pubkey),
                    {"mint": token_address},
                    {"encoding": "jsonParsed"}
                ]
            )
            
            accounts = response.get('result', {}).get('value', [])
            if not accounts:
                return BalanceResult(
                    code=BalanceErrorCode.SUCCESS,
                    value=0.0,
                    message="No token accounts found"
                )
                
            token_data = accounts[0]['account']['data']['parsed']['info']['tokenAmount']
            balance = TokenBalance(
                amount=int(token_data['amount']),
                decimals=int(token_data['decimals'])
            )
            
            return BalanceResult(
                code=BalanceErrorCode.SUCCESS,
                value=balance.formatted_amount
            )
            
        except RateLimitError as e:
            return BalanceResult(
                code=BalanceErrorCode.RATE_LIMIT_EXCEEDED,
                message=str(e)
            )
        except Exception as e:
            error_code, error_message = self._classify_error(e)
            return BalanceResult(
                code=error_code,
                message=f"Failed to get token balance: {error_message}"
            )

    def _get_sol_balance(self, wallet_pubkey: Pubkey) -> BalanceResult:
        """Get SOL balance with error handling"""
        try:
            response = self.client.get_balance(wallet_pubkey)
            balance = float(response.value) / (10 ** self.SOL_DECIMALS)
            
            return BalanceResult(
                code=BalanceErrorCode.SUCCESS,
                value=balance
            )
            
        except Exception as e:
            error_code, error_message = self._classify_error(e)
            return BalanceResult(
                code=error_code,
                message=f"Failed to get SOL balance: {error_message}"
            )
'''
# get_report 사용법
    get_report() 함수를 호출하면 응답은 BalanceResult 객체의 리스트로 반환됩니다.
    - 정상:
    [BalanceResult(code=<BalanceErrorCode.SUCCESS: 0>,
                value=12.132280103,
                message=None,
                ticker='SOL',
                address=None),
    BalanceResult(code=<BalanceErrorCode.SUCCESS: 0>,
                value=65000.418741202,
                message=None,
                ticker='AI16Z',
                address='HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC')]
    - 오류시:
    BalanceResult(code=<BalanceErrorCode.UNKNOWN_ERROR: 4>,
              value=None,
              message='Fatal error: Failed to connect to any Solana RPC '
                      'endpoint. Last error: DNS_ERROR: DNS resolution failed',
              ticker=None,
              address=None)
'''
def get_report(sol_account = None ,addresses: Optional[Dict[str, str]] = None, provider_urls = None) -> Union[list[BalanceResult], BalanceResult]:
    if not sol_account: # 파라미터 전달안하면 .env 환경변수에서 가져옴
        load_dotenv()
        account = os.getenv("PHANTOM_SOLANA_ACCOUNT")
        if not account:
            logger.error("Error: PHANTOM_SOLANA_ACCOUNT environment variable not set")
    else:
        account = sol_account
    
    if not addresses: # 파라미터 전달안하면 설정
        token_addresses = {
            "SOL": None,
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        }
    else:
        token_addresses = addresses

    if not provider_urls:  # 파라미터 전달안하면 설정
        provider_urls = [
            "https://api.mainnet-beta.solana.com",
        ]
    else:
        provider_urls = provider_urls


    try:
        max_retries = 3
        retry_delay = 10
        retry_count = 0
        while retry_count < max_retries:
            try:
                solana_api = SolanaApi(account, provider_urls)
                # print("init...", solana_api)
                break
            except ConnectionError as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"Connection error: {str(e)}. Retrying {retry_count}/{max_retries} in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to initialize SolanaApi after {max_retries} attempts: {str(e)}")
                    return BalanceResult(
                        code=BalanceErrorCode.CONNECTION_ERROR,
                        message=f"Failed to initialize SolanaApi after {max_retries} attempts: {str(e)}"
                    )

        wallet_balances = []
        for name, address in token_addresses.items():
            max_retries = 3
            base_delay = 15
            retry_count = 0
            while retry_count < max_retries:
                try:
                    result = solana_api.get_wallet_balance(address)

                    if result.is_success:
                        logger.info(f"{name} Balance: {result.value:.6f}")
                        result.ticker = name
                        result.address = address 
                        # print(result)
                        wallet_balances.append(result)
                        break
                    else:
                        if result.code == BalanceErrorCode.RATE_LIMIT_EXCEEDED:
                            retry_count += 1
                            wait_time = base_delay * (2 ** retry_count)
                            logger.warning(f"Rate limit reached for {name}, waiting {wait_time} seconds... (attempt {retry_count}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                        logger.error(f"Error fetching {name} balance: [{result.code.name}] {result.message}")
                        break

                except Exception as e:
                    error_code, error_message = solana_api._classify_error(e)
                    if error_code == BalanceErrorCode.RATE_LIMIT_EXCEEDED:
                        retry_count += 1
                        wait_time = base_delay * (2 ** retry_count)
                        logger.warning(f"Rate limit reached for {name}, waiting {wait_time} seconds... (attempt {retry_count}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    logger.error(f"Error processing {name}: {error_message}")
                    break

            if retry_count >= max_retries:
                logger.error(f"Max retries reached for {name}, skipping...")
                return BalanceResult(
                    code=BalanceErrorCode.MAX_RETRIES_EXCEEDED,
                    message=f"Fatal error: Max retries reached for {name}"
                )
        
        return wallet_balances
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return BalanceResult(
            code=BalanceErrorCode.UNKNOWN_ERROR,
            message=f"Fatal error: {str(e)}"
        )

"""
  currency     balance        price           total                 date
0    AI16Z 65,000.4187     812.0000 52,780,340.0179  2025-02-01 21:59:16
1      SOL     12.1323 352,000.0000  4,270,562.5963  2025-02-01 21:59:16
2     USDC     25.2817   1,538.0000     38,883.2285  2025-02-01 21:59:16
"""
from typing import Optional, Dict
from datetime import datetime
import pandas as pd
from logging import getLogger
from utils.price_fetcher import PriceAPI

def get_df_report(sol_account=None, addresses: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """
    Generate a DataFrame report with currency balances and their KRW values.
    
    Args:
        sol_account: Solana account information
        addresses: Optional dictionary of addresses
    
    Returns:
        pd.DataFrame with columns: currency, balance, price, total, date
        or BalanceResult in case of error
    """
    try:
        # Initialize PriceAPI
        price_api = PriceAPI()
        
        # Get the balance report
        report = get_report(sol_account, addresses)
        # print(report)

        if isinstance(report, BalanceResult):
            raise Exception(f"Error: {report.message}")
        
        data = []
        for result in report:
            if result.is_success:
                # Get the current price for the currency
                price_krw, exchange = price_api.get_first_valid_price(result.ticker.lower())
                
                # Calculate total value in KRW
                total_value = float(result.value) * price_krw
                
                data.append({
                    "currency": result.ticker,
                    "balance": result.value,
                    "price": price_krw,
                    "total": total_value,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    # "exchange": exchange  # Optional: Include exchange information
                })
        
        # Create DataFrame
        df = pd.DataFrame(data)

        # Format numeric columns
        if not df.empty:
            # Round numeric values for better readability
            df['balance'] = df['balance'].astype(float)
            df['price'] = df['price'].astype(float)
            df['total'] = df['total'].astype(float)
            
            # Sort by total value descending
            df = df.sort_values('total', ascending=False)
            
            pd.set_option('display.float_format', lambda x: '{:,.4f}'.format(x))            
            # Reset index after sorting
            df = df.reset_index(drop=True)
        
        return df
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return BalanceResult(
            code=BalanceErrorCode.UNKNOWN_ERROR,
            message=f"Fatal error: {str(e)}"
        )
    

def sample_usage():

    if 0: # 따로 파라미터 설정안하면 기본적으로 클래스에서 정의해논 값으로 그냥 씁니다. 귀찮아서 만들었음.
        resp = get_report()
        if isinstance(resp, list):  # 정상적인 리스트 응답
            filtered = [(r.ticker, r.value if r.value is not None and r.value >= 0.0 else None) for r in resp]
            print(f"{filtered}")
            print()

        elif isinstance(resp, BalanceResult):  # 단일응답, 또는 에러응답
            print(f"Error: {resp.message}")
            raise Exception(f"Error: {resp.message}")
        else:
            raise ValueError("Unsupported response format!!")

    if 0: # 소스에 모두 설정하는 경우
        load_dotenv()
        sol_account = os.getenv("PHANTOM_SOLANA_ACCOUNT")
        if not sol_account:
            logger.error("Error: PHANTOM_SOLANA_ACCOUNT environment variable not set")
            # print (BalanceErrorCode.UNKNOWN_ERROR, "PHANTOM_SOLANA_ACCOUNT environment variable not set")

        token_addresses = {
            "SOL": None,
            "AI16Z": "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC",
            "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        }

        resp = get_report(sol_account, token_addresses)
        if isinstance(resp, list):  # 정상적인 리스트 응답
            filtered = [(r.ticker, r.value if r.value is not None and r.value >= 0.0 else None) for r in resp]
            print(f"{filtered}")
            print()

        elif isinstance(resp, BalanceResult):  # 단일응답, 또는 에러응답
            print(f"Error: {resp.message}")
            raise Exception(f"Error: {resp.message}")
        else:
            raise ValueError("Unsupported response format!!")


    if 1: # pandas df 포맷으로 응답해주기
        load_dotenv()
        sol_account = os.getenv("PHANTOM_SOLANA_ACCOUNT")
        if not sol_account:
            logger.error("Error: PHANTOM_SOLANA_ACCOUNT environment variable not set")
            # print (BalanceErrorCode.UNKNOWN_ERROR, "PHANTOM_SOLANA_ACCOUNT environment variable not set")

        token_addresses = {
            "SOL": None,
            "AI16Z": "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC",
            # "ARGO": "Argoo945JjG9oyt5hgsrdtwbG3S4ATXQy4tTdYMzsV1m",
            # "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        }

        df = get_df_report(sol_account, token_addresses)
        if isinstance(df, pd.DataFrame):  # 정상적인 리스트 응답
            # 결과를 출력해준다!!! dataframe 포맷에 맞춰서!!!
            print(df)
            print()

        elif isinstance(df, BalanceResult):  # 단일응답, 또는 에러응답
            raise Exception(f"Error: {df.message}")
        else:
            raise ValueError("Unsupported response format")
 


if __name__ == "__main__":
    try:
        resp = sample_usage()
        if resp != None:
            raise Exception(f"{resp.message}")
        print("Good Job!!")
    except Exception as e:
        logger.error(f"비정상으로 수행되었습니다: {str(e)}")




