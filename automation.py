import json
import time
import requests
import datetime
import http.client
import pandas as pd
import pandas_ta as ta
import numpy as np
from numba import njit  
from bs4 import BeautifulSoup as bs
from config import API_URL, HEADERS, CLIENT_ID, CLIENT_PIN, STATE_VARIABLE

def login_to_angel_one(totp):
    conn = http.client.HTTPSConnection(API_URL)
    payload = json.dumps({
        "clientcode": CLIENT_ID,
        "password": CLIENT_PIN,
        "totp": totp,
        "state": STATE_VARIABLE
    })
    
    headers = {**HEADERS, 'Content-Type': 'application/json'}
    conn.request("POST", "/rest/auth/angelbroking/user/v1/loginByPassword", payload, headers)

    res = conn.getresponse()
    data = res.read().decode("utf-8")
    return json.loads(data)

def make_request(method, endpoint, payload=None, auth_token=None):
    conn = http.client.HTTPSConnection(API_URL)
    headers = HEADERS.copy()
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    if payload:
        headers['Content-Type'] = 'application/json'
        payload = json.dumps(payload)
    else:
        payload = ''
    conn.request(method, endpoint, payload, headers)
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")

def get_historical_data(auth_token, symboltoken):
    payload = {
        "exchange": "NSE",
        "symboltoken": symboltoken,
        "interval": "ONE_MINUTE",
        "fromdate": "2025-03-03 09:00",
        "todate": "2025-03-03 15:30"
    }
    time.sleep(2)
    response = make_request("POST", "/rest/secure/angelbroking/historical/v1/getCandleData", payload, auth_token)
    response = json.loads(response)
    if response.get("status") and response.get("data"):
        return response['data']
    else:
        return None

def supertrend(df, atr_multiplier):
    current_avg = (df['high'] + df['low']) / 2
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], period=10)
    df.dropna(inplace=True)

    df['basicUpperband'] = current_avg + (atr_multiplier * df['atr'])
    df['basicLowerband'] = current_avg - (atr_multiplier * df['atr'])

    # Convert to float64 to avoid dtype=object issues
    basicUpper = np.asarray(df['basicUpperband'].values, dtype=np.float64)
    basicLower = np.asarray(df['basicLowerband'].values, dtype=np.float64)
    close_vals = np.asarray(df['close'].values, dtype=np.float64)

    # Use Numba accelerated computation for bands
    upperBand, lowerBand = compute_bands(basicUpper, basicLower, close_vals)
    
    df['upperband'] = upperBand
    df['lowerband'] = lowerBand
    df.drop(['basicUpperband', 'basicLowerband'], axis=1, inplace=True)
    return df

@njit
def compute_bands(basicUpper, basicLower, close):
    n = len(basicUpper)
    upperBand = np.empty(n)
    lowerBand = np.empty(n)
    upperBand[0] = basicUpper[0]
    lowerBand[0] = basicLower[0]
    for i in range(1, n):
        if basicUpper[i] < upperBand[i-1] or close[i-1] > upperBand[i-1]:
            upperBand[i] = basicUpper[i]
        else:
            upperBand[i] = upperBand[i-1]
        if basicLower[i] > lowerBand[i-1] or close[i-1] < lowerBand[i-1]:
            lowerBand[i] = basicLower[i]
        else:
            lowerBand[i] = lowerBand[i-1]
    return upperBand, lowerBand

@njit
def compute_indicator(close, upperband, lowerband):
    n = len(close)
    indicators = np.empty(n, dtype=np.int8)
    indicators[0] = 1  
    for i in range(1, n):
        if close[i] > upperband[i]:
            indicators[i] = 1
        elif close[i] < lowerband[i]:
            indicators[i] = -1
        else:
            indicators[i] = indicators[i-1]
    return indicators

def calculate_supertrend_indicator(df):
    close_vals = df['close'].values
    upperband_vals = df['upperband'].values
    lowerband_vals = df['lowerband'].values
    indicators_num = compute_indicator(close_vals, upperband_vals, lowerband_vals)
    indicators_str = ["Green" if x == 1 else "Red" for x in indicators_num]
    df['Supertrend'] = indicators_str
    return df

def stock_selection_filter(stock_data):
    selected_stocks = {}
    for token, df in stock_data.items():
        daily = df.resample('D').agg({
            'open': 'first', 
            'high': 'max', 
            'low': 'min', 
            'close': 'last', 
            'volume': 'sum'
        })
        daily.dropna(inplace=True)
        if len(daily) < 3:
            selected_stocks[token] = df
            continue
        selected_stocks[token] = df
        
    signals = {}
    buy_details_dict = {}

    for token in stock_data.keys():
        if token not in signals:
            signals[token] = None
        if token not in buy_details_dict:
            buy_details_dict[token] = None
    
    
    return selected_stocks

def process_stock(auth_token, symboltoken):
    json_str = get_historical_data(auth_token, symboltoken)
    data_json = json_str
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    if isinstance(data_json, dict) and 'data' in data_json:
        records = data_json['data']
    else:
        records = data_json
    df = pd.DataFrame(records, columns=cols)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df = df.between_time('09:15', '15:30')
    df['EMA9'] = df['close'].ewm(span=7, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    df = supertrend(df, atr_multiplier=7) 
    df = calculate_supertrend_indicator(df)
    df_30 = supertrend(df.copy(), atr_multiplier=30)
    df_30 = calculate_supertrend_indicator(df_30)
    df['Supertrend_30'] = df_30['Supertrend']
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    df = pd.concat([df, macd], axis=1)
    df.dropna(inplace=True)
    return symboltoken, df

def livetest_data():
    url = 'https://chartink.com/screener/process'
    condition = {
        "scan_clause": "( {cash} ( 1 day ago \"close - 1 candle ago close / 1 candle ago close * 100\" < -3 and 1 day ago volume > 20000 and 2 days ago volume > 20000 and 3 days ago volume > 20000 and weekly volume > 50000 and latest \"close - 1 candle ago close / 1 candle ago close * 100\" >= 0.01 and monthly \"close - 1 candle ago close / 1 candle ago close * 100\" > 1 and weekly \"close - 1 candle ago close / 1 candle ago close * 100\" > 1 and latest close >= 300 and latest close <= 5000 ) ) "
    }
    with requests.session() as s:
        r_data = s.get(url)
        soup = bs(r_data.content, 'lxml')
        meta = soup.find('meta', {'name': 'csrf-token'})['content']
        headers = {"x-csrf-token": meta}
        data = s.post(url, data=condition, headers=headers).json()
        stock_List = pd.DataFrame(data['data'])
        nse_list = stock_List['nsecode'].tolist()
        print(nse_list) # in form of name, should be converted to token
       
    return nse_list


def backtest_data():
    url = 'https://chartink.com/backtest/process'
    condition = {
        "scan_clause": "( {cash} ( 1 day ago \"close - 1 candle ago close / 1 candle ago close * 100\" < -3 and 1 day ago volume > 20000 and 2 days ago volume > 20000 and 3 days ago volume > 20000 and weekly volume > 50000 and latest \"close - 1 candle ago close / 1 candle ago close * 100\" >= 0.01 and monthly \"close - 1 candle ago close / 1 candle ago close * 100\" > 1 and weekly \"close - 1 candle ago close / 1 candle ago close * 100\" > 1 ) ) "
    }
    with requests.session() as s:
        r_data = s.get("https://chartink.com/screener/process")
        soup = bs(r_data.content, 'lxml')
        meta = soup.find('meta', {'name': 'csrf-token'})['content']
        headers = {"x-csrf-token": meta}
        data = s.post(url, data=condition, headers=headers).json()
        dates = data["metaData"][0]["tradeTimes"]
        stocks = data["aggregatedStockList"]
        final_data = []
        for i in range(len(dates)):
            stk = []
            if stocks[i]:
                for j in range(len(stocks[i])):
                    if j % 3 == 0:
                        stk.append(stocks[i][j])
                final_data.append({
                    "Date": datetime.datetime.fromtimestamp(dates[i] / 1000).strftime("%Y-%m-%d"),
                    "Stock": stk
                })

    with open("stock_data.json", "w") as json_file:
        json.dump(final_data, json_file, indent=4)

    return final_data