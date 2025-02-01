예시
<pre>
[2025-02-01 22:45:04] 업데이트 완료. 3분 대기중...
[2025-02-01 22:48:08] 포트폴리오 업데이트 시작
[2025-02-01 22:48:08] ./agg.py 실행중...
2025-02-01 22:48:14,274 - INFO - Attempting to connect to https://api.mainnet-beta.solana.com
2025-02-01 22:48:14,677 - INFO - HTTP Request: POST https://api.mainnet-beta.solana.com "HTTP/1.1 200 OK"
2025-02-01 22:48:14,678 - INFO - Successfully connected to https://api.mainnet-beta.solana.com
2025-02-01 22:48:14,721 - INFO - HTTP Request: POST https://api.mainnet-beta.solana.com "HTTP/1.1 200 OK"
2025-02-01 22:48:14,722 - INFO - SOL Balance: 1.132280
2025-02-01 22:48:15,044 - INFO - USDC Balance: 25.281683
  currency     balance        price           total                 date
0      SOL      2.1323 350,050.0000  4,246,904.6501  2025-02-01 22:48:15
1     USDC     25.2817   1,537.0000     38,857.9468  2025-02-01 22:48:15
- -----------------------------
   currency     balance             price           total                 date exchange
0       BTC      0.0910  156,967,000.0000    773,775.6800  2025-02-01 22:48:15   Korbit
1       BTC      0.0108  156,825,000.0000    422,845.8943  2025-02-01 22:48:15    Upbit
2     AI16Z      0.4187          806.0000    390,337.5054  2025-02-01 22:48:15  Phantom
3       SOL      0.8006      350,050.0000     35,815.0927  2025-02-01 22:48:15    Upbit
4       SOL      0.1323      350,050.0000    246,904.6501  2025-02-01 22:48:15  Phantom
5       FET     29.1513        1,552.0000     45,242.8627  2025-02-01 22:48:15  Bithumb
6      USDC     25.2817        1,537.0000     38,857.9468  2025-02-01 22:48:15  Phantom
7      LINK      1.0000       37,850.0000     37,850.0000  2025-02-01 22:48:15    Upbit
- -----------------------------
포트폴리오 합계: ₩000,205,005
- -----------------------------
</pre>

.env 별도 생성 같은 위치에 저장
<pre>

UPBIT_ACCESS_KEY= "NT1111111111111A"
UPBIT_SECRET_KEY= "NT1111111111111A"

KORBIT_ACCESS_KEY= "NT1111111111111A"
KORBIT_SECRET_KEY= "NT1111111111111A"

BITHUMB_ACCESS_KEY = "NT1111111111111A"
BITHUMB_SECRET_KEY = "NT1111111111111A=="

COINONE_ACCESS_KEY = "NT1111111111111A"
COINONE_SECRET_KEY = "NT1111111111111A"

KEY_BNC_API = "NT1111111111111A"
KEY_BNC_SECRET = "NT1111111111111A"

KEY_OKX_API = "NT1111111111111A"
KEY_OKX_SECRET = "NT1111111111111A"
KEY_OKX_PASSPHRASE= "NT1111111111111A!"

PHANTOM_SOLANA_ACCOUNT = "NT1111111111111A"

# 보유수량
CRYPTO_BTC=1.00
CRYPTO_SOL=1.0
CRYPTO_AI16Z=1.00
CRYPTO_FET=1.00
CRYPTO_LINK=1
CRYPTO_VIRTUAL=1.00
CRYPTO_SUI=1.00
CRYPTO_KRW=1.00
CRYPTO_USDC=1.0
CRYPTO_ETH=1.00



  
</pre>
