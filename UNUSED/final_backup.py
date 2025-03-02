from datetime import date
import os
import requests
import json
from bs4 import BeautifulSoup as bs
import datetime
import time
import http.client
import pandas as pd
import numpy as np
from numpy import nan as npNaN
import pandas_ta as ta
from warnings import filterwarnings
filterwarnings('ignore')
from multiprocessing import Pool, cpu_count 
from numba import njit  
AUTH_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VybmFtZSI6Ikg4ODUyMiIsInJvbGVzIjowLCJ1c2VydHlwZSI6IlVTRVIiLCJ0b2tlbiI6ImV5SmhiR2NpT2lKU1V6STFOaUlzSW5SNWNDSTZJa3BYVkNKOS5leUoxYzJWeVgzUjVjR1VpT2lKamJHbGxiblFpTENKMGIydGxibDkwZVhCbElqb2lkSEpoWkdWZllXTmpaWE56WDNSdmEyVnVJaXdpWjIxZmFXUWlPallzSW5OdmRYSmpaU0k2SWpNaUxDSmtaWFpwWTJWZmFXUWlPaUl3TkRrek1XTmlZeTB3WkRFeExUTmpNelF0WWpOaU5DMDNOakk0TWprMlpEa3hZV0lpTENKcmFXUWlPaUowY21Ga1pWOXJaWGxmZGpJaUxDSnZiVzVsYldGdVlXZGxjbWxrSWpvMkxDSndjbTlrZFdOMGN5STZleUprWlcxaGRDSTZleUp6ZEdGMGRYTWlPaUpoWTNScGRtVWlmU3dpYldZaU9uc2ljM1JoZEhWeklqb2lZV04wYVhabEluMTlMQ0pwYzNNaU9pSjBjbUZrWlY5c2IyZHBibDl6WlhKMmFXTmxJaXdpYzNWaUlqb2lTRGc0TlRJeUlpd2laWGh3SWpveE56UXdPVFE0TnpNMExDSnVZbVlpT2pFM05EQTROakl4TlRRc0ltbGhkQ0k2TVRjME1EZzJNakUxTkN3aWFuUnBJam9pTUdFNE1UWTRabUV0TW1VMU1pMDBOamRoTFdGbFlUTXRNMlV3WTJWaE1EbGtZamN5SWl3aVZHOXJaVzRpT2lJaWZRLlFWcF9JaTVWQjZ5cHpoRTU5bU9BQWZCVUExMndtUjZHTDFiUlVsLW1aSG9TYVZqTWFCdDlVbWRkblVkaW0tLTU3OC12VWlhZzJSdWY5czduUFpPeGJNX20wWEJ1b1VCUkFuVXl0cGNQUWJvVjJfR1NraElaRnFSZ3ljNW83WklSM1hDR1F4TklrWXpZcTRwc1R2amgtTUo4NGltYXM3cUlIQWRxX0M2ZzhtQSIsIkFQSS1LRVkiOiJwcVpLQzI4NSIsImlhdCI6MTc0MDg2MjMzNCwiZXhwIjoxNzQwOTQ4NzM0fQ.VRMf9hcB2RIaTAMzMKL4kzaiexTW0I-gt28nKJhD09_58RedtxjnoqIUr93H9l9HKHHKIGte5n8_r-ZP2ArY0w"
API_URL = "apiconnect.angelone.in"
HEADERS = {
  'X-PrivateKey': 'pqZKC285',
  'Accept': 'application/json',
  'X-SourceID': 'WEB',
  'X-ClientLocalIP': 'CLIENT_LOCAL_IP',
  'X-ClientPublicIP': 'CLIENT_PUBLIC_IP',
  'X-MACAddress': 'MAC_ADDRESS',
  'X-UserType': 'USER',
  'Authorization': f'Bearer {AUTH_TOKEN}',
  'Content-Type': 'application/json'
}

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

def get_transaction_charges(product_type, transaction_type, quantity, price, token, symbol_name, auth_token=None):
    payload = {
        "orders": [
            {
                "product_type": product_type,
                "transaction_type": transaction_type,
                "quantity": str(quantity),
                "price": str(price),
                "exchange": "NSE",
                "symbol_name": symbol_name,
                "token": token
            }
        ]
    }
    response_str = make_request("POST", "/rest/secure/angelbroking/brokerage/v1/estimateCharges", payload, auth_token)
    response = json.loads(response_str)
    if response.get("status") and response.get("data") and "summary" in response["data"]:
        total_charges = response["data"]["summary"].get("total_charges", 0)
        return total_charges
    else:
        return 0
profit_count = 0
loss_count = 0
delivery_count = 0
no_trade_count = 0
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

def supertrend(df, atr_multiplier):
    current_avg = (df['high'] + df['low']) / 2
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], period=10)
    df.dropna(inplace=True)
    df['basicUpperband'] = current_avg + (atr_multiplier * df['atr'])
    df['basicLowerband'] = current_avg - (atr_multiplier * df['atr'])
    # Use Numba accelerated computation for bands
    basicUpper = df['basicUpperband'].values
    basicLower = df['basicLowerband'].values
    close_vals = df['close'].values
    upperBand, lowerBand = compute_bands(basicUpper, basicLower, close_vals)
    
    df['upperband'] = upperBand
    df['lowerband'] = lowerBand
    df.drop(['basicUpperband', 'basicLowerband'], axis=1, inplace=True)
    return df

def calculate_supertrend_indicator(df):
    close_vals = df['close'].values
    upperband_vals = df['upperband'].values
    lowerband_vals = df['lowerband'].values
    indicators_num = compute_indicator(close_vals, upperband_vals, lowerband_vals)
    indicators_str = ["Green" if x == 1 else "Red" for x in indicators_num]
    df['Supertrend'] = indicators_str
    return df

def resample_ohlc(df, timeframe):
    df_resampled = pd.DataFrame()
    df_resampled['open'] = df['open'].resample(timeframe).first()
    df_resampled['high'] = df['high'].resample(timeframe).max()
    df_resampled['low'] = df['low'].resample(timeframe).min()
    df_resampled['close'] = df['close'].resample(timeframe).last()
    df_resampled['volume'] = df['volume'].resample(timeframe).sum()
    df_resampled.dropna(inplace=True)
    return df_resampled

def get_historical_data(symboltoken):
    file_path = os.path.join("stock_data", f"{symboltoken}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                data_json = json.load(file)
                return data_json
            except json.decoder.JSONDecodeError as e:
                print(f"Error decoding JSON for symbol {symboltoken}: {e}")
                return None
    else:
        print(f"File not found for symbol {symboltoken}")
        return None

def check_signals(df, user_datetime, last_signal, portfolio_balance, delivery_balance, symboltoken, buy_details=None):
    global profit_count, loss_count, no_trade_count, delivery_count, token_to_name
    if df.index.tz is not None:
        user_datetime = user_datetime.tz_localize(df.index.tz)
    window_start = user_datetime - pd.Timedelta(minutes=1)
    df_filtered = df.loc[window_start:user_datetime]
    for i in range(1, len(df_filtered)):
        current_close = df_filtered['close'].iloc[i]
        current_supertrend = df_filtered['Supertrend'].iloc[i]
        current_ema50 = df_filtered['EMA50'].iloc[i]
        if last_signal != "buy" and portfolio_balance > 0:
            if (df_filtered['EMA9'].iloc[i-1] <= df_filtered['EMA21'].iloc[i-1] and 
                df_filtered['EMA9'].iloc[i] > df_filtered['EMA21'].iloc[i] and 
                user_datetime.time() < pd.to_datetime('13:05').time()):
                if (current_supertrend == "Green" and 
                    df_filtered['Supertrend_30'].iloc[i] == "Green" and 
                    current_ema50 <= current_close and 
                    df_filtered['MACDh_12_26_9'].iloc[i] > 1):
                    shares_to_buy = int(portfolio_balance // current_close)
                    if shares_to_buy > 0:
                        cost = shares_to_buy * current_close
                        charges = get_transaction_charges("INTRADAY", "BUY", shares_to_buy, current_close, symboltoken, token_to_name.get(symboltoken, symboltoken), AUTH_TOKEN)
                        total_cost = cost + charges
                        portfolio_balance -= total_cost
                        buy_details = (current_close, shares_to_buy)
                        print(f"Buy Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {shares_to_buy} of {symboltoken}, Charges: {charges:.2f}")
                        return "buy", buy_details, portfolio_balance, delivery_balance
        if last_signal == "delivery" and buy_details is not None:
            if current_close >= buy_details[0] * 1.008:
                proceeds = buy_details[1] * current_close
                charges = get_transaction_charges("DELIVERY", "SELL", buy_details[1], current_close, symboltoken, token_to_name.get(symboltoken, symboltoken), AUTH_TOKEN)
                net_proceeds = proceeds - charges
                portfolio_balance += net_proceeds
                print(f"Delivery Sell on Profit at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken}, Charges: {charges:.2f}")
                profit_count += 1
                return "sell", None, portfolio_balance, delivery_balance
            elif current_close <= buy_details[0] * 0.97:
                proceeds = buy_details[1] * current_close
                charges = get_transaction_charges("DELIVERY", "SELL", buy_details[1], current_close, symboltoken, token_to_name.get(symboltoken, symboltoken), AUTH_TOKEN)
                net_proceeds = proceeds - charges
                portfolio_balance += net_proceeds
                print(f"Delivery Sell on Loss at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken}, Charges: {charges:.2f}")
                loss_count += 1
                return "sell", None, portfolio_balance, delivery_balance
            else:
                return "delivery", buy_details, portfolio_balance, delivery_balance
        if last_signal == "buy" and buy_details is not None:
            one_week_ago = df_filtered.index[i] - pd.Timedelta(days=7)
            past_week = df.loc[one_week_ago:df_filtered.index[i]]
            if not past_week.empty:
                avg_close = past_week['close'].mean()
            else:
                avg_close = current_close
            if (current_close <= buy_details[0] and user_datetime.time() > pd.to_datetime('15:14').time()):
                if current_supertrend == "Green":
                    continue  
                elif current_supertrend == "Red":
                    conversion_amount = buy_details[0] * buy_details[1]
                    if delivery_balance >= conversion_amount:
                        delivery_count += 1
                        delivery_balance -= conversion_amount
                        portfolio_balance += conversion_amount
                        print(f"Convert to Delivery at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken}")
                        return "delivery", buy_details, portfolio_balance, delivery_balance
                    else:
                        charges = get_transaction_charges("INTRADAY", "SELL", buy_details[1], current_close, symboltoken, token_to_name.get(symboltoken, symboltoken), AUTH_TOKEN)
                        proceeds = buy_details[1] * current_close
                        net_proceeds = proceeds - charges
                        portfolio_balance += net_proceeds
                        print(f"Cannot Convert to Delivery, Sell Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken} (Loss from Buy), Charges: {charges:.2f}")
                        loss_count += 1
                        return "sell", None, portfolio_balance, delivery_balance
            if (df_filtered['EMA9'].iloc[i-1] >= df_filtered['EMA21'].iloc[i-1] and 
                df_filtered['EMA9'].iloc[i] < df_filtered['EMA21'].iloc[i]):
                if current_supertrend == "Red" and current_ema50 >= current_close and current_close >= buy_details[0]:
                    proceeds = buy_details[1] * current_close
                    charges = get_transaction_charges("INTRADAY", "SELL", buy_details[1], current_close, symboltoken, token_to_name.get(symboltoken, symboltoken), AUTH_TOKEN)
                    net_proceeds = proceeds - charges
                    portfolio_balance += net_proceeds
                    print(f"Sell Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken} (Profit from Buy), Charges: {charges:.2f}")
                    profit_count += 1
                    return "sell", None, portfolio_balance, delivery_balance
            if buy_details[0] <= current_close * 0.97 and user_datetime.time() > pd.to_datetime('15:10').time():
                proceeds = buy_details[1] * current_close
                charges = get_transaction_charges("INTRADAY", "SELL", buy_details[1], current_close, symboltoken, token_to_name.get(symboltoken, symboltoken), AUTH_TOKEN)
                net_proceeds = proceeds - charges
                portfolio_balance += net_proceeds
                print(f"Sell Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken} (Early Profit from Buy), Charges: {charges:.2f}")
                profit_count += 1
                return "sell", None, portfolio_balance, delivery_balance
            if buy_details[0] <= current_close * 0.96:
                proceeds = buy_details[1] * current_close
                charges = get_transaction_charges("INTRADAY", "SELL", buy_details[1], current_close, symboltoken, token_to_name.get(symboltoken, symboltoken), AUTH_TOKEN)
                net_proceeds = proceeds - charges
                portfolio_balance += net_proceeds
                print(f"Sell Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken} (Early Profit from Buy), Charges: {charges:.2f}")
                profit_count += 1
                return "sell", None, portfolio_balance, delivery_balance
            if pd.to_datetime('15:10').time() < user_datetime.time() < pd.to_datetime('15:55').time():
                proceeds = buy_details[1] * current_close
                if current_close < buy_details[0]:
                    conversion_amount = buy_details[0] * buy_details[1]
                    if delivery_balance >= conversion_amount:
                        delivery_count += 1
                        delivery_balance -= conversion_amount
                        portfolio_balance += conversion_amount
                        print(f"Convert to Delivery at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken}")
                        return "delivery", buy_details, portfolio_balance, delivery_balance
                    else:
                        charges = get_transaction_charges("INTRADAY", "SELL", buy_details[1], current_close, symboltoken, token_to_name.get(symboltoken, symboltoken), AUTH_TOKEN)
                        net_proceeds = proceeds - charges
                        portfolio_balance += net_proceeds
                        print(f"Cannot Convert to Delivery, Sell Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken} (Loss from Buy), Charges: {charges:.2f}")
                        loss_count += 1
                        return "sell", None, portfolio_balance, delivery_balance
                else:
                    charges = get_transaction_charges("INTRADAY", "SELL", buy_details[1], current_close, symboltoken, token_to_name.get(symboltoken, symboltoken), AUTH_TOKEN)
                    net_proceeds = proceeds - charges
                    portfolio_balance += net_proceeds
                    print(f"Sell Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken} (Profit from Buy), Charges: {charges:.2f}")
                    profit_count += 1
                    return "sell", None, portfolio_balance, delivery_balance
    no_trade_count += 1
    return last_signal, buy_details, portfolio_balance, delivery_balance

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
    return selected_stocks

def process_stock(symboltoken):
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, f"{symboltoken}_processed.pkl")
    if os.path.exists(temp_file):
        df = pd.read_pickle(temp_file)
        return symboltoken, df, None, None
    json_str = get_historical_data(symboltoken)
    data_json = json_str
    if data_json is None:
        print(f"Skipping symbol {symboltoken}")
        return symboltoken, None, None, None
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
    df.to_pickle(temp_file)
    return symboltoken, df, None, None

def main():
    import sys
    log_file = open("log.txt", "w")
    class Logger(object):
        def __init__(self, file):
            self.terminal = sys.stdout
            self.log = file
        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
        def flush(self):
            self.terminal.flush()
            self.log.flush()
    sys.stdout = Logger(log_file)
    content = "FZJ4hJyY6uXw2bkrioEqQkjR1Lq418Bd5ckIbuz3"
    url = 'https://chartink.com/backtest/process'
    condition = {"scan_clause": "( {cash} ( latest rsi( 9 ) > 70 and latest volume > 50000 and latest close >= 200 and latest close <= 5000 and latest close - 1 candle ago close / 1 candle ago close * 100 >= 0.02 ) ) "}
    
    # Caching Chartink data in a temp file
    cache_file = "chartink_cache.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            data = json.load(f)
    else:
        with requests.session() as s:
            r_data = s.get("https://chartink.com/screener/process")
            soup = bs(r_data.content, 'lxml')
            meta = soup.find('meta', {'name': 'csrf-token'})['content']
            headers = {"x-csrf-token": meta}
            data = s.post(url, data=condition, headers=headers).json()
        with open(cache_file, "w") as f:
            json.dump(data, f)
    
    date = data["metaData"][0]["tradeTimes"]
    stock = data["aggregatedStockList"]
    final_data = []
    for i in range(0, len(date)):
        stk = []
        if stock[i] != []:
            for j in range(len(stock[i])):
                if j % 3 == 0:
                    stk.append(stock[i][j])
            final_data.append(
                {
                    "Date": datetime.datetime.fromtimestamp(date[i]/1000),
                    "Stock": stk
                }
            )
    date_to_stocks = {}
    for record in final_data:
        record_date = record['Date'].date()
        date_to_stocks[record_date] = record['Stock']
    with open('stockList.json', 'r') as file:
        stock_data = json.load(file)
    name_to_token = {entry["name"]: entry["token"] for entry in stock_data}
    global token_to_name
    token_to_name = {entry["token"]: entry["name"] for entry in stock_data}
    portfolio_balance = 10000
    delivery_balance = 30000
    signals = {}
    buy_details_dict = {}
    print(f"Initial portfolio balance: {portfolio_balance:.2f}\n")
    print(f"Initial delivery balance: {delivery_balance:.2f}\n")
    delivery_stocks = {} 
    current_stocks = []
    start_datetime = pd.Timestamp("2025-01-01 09:15")
    current_datetime = pd.Timestamp.now()
    while start_datetime <= current_datetime:
        if start_datetime.time() == pd.to_datetime('09:15').time():
            current_date = start_datetime.date()
            current_day_stocks = date_to_stocks.get(current_date, [])
            stocks_new = [name_to_token[stock] for stock in current_day_stocks if stock in name_to_token]
            sorted_dates = sorted(date_to_stocks.keys())
            prev_date = None
            if current_date in sorted_dates:
                idx = sorted_dates.index(current_date)
                if idx > 0:
                    prev_date = sorted_dates[idx - 1]
            prev_day_stocks = date_to_stocks.get(prev_date, []) if prev_date else []
            stocks_prev = [name_to_token[stock] for stock in prev_day_stocks if stock in name_to_token]
            new_stocks = list(set(stocks_new) - set(stocks_prev))
            current_stocks = list(set(new_stocks) | set(delivery_stocks.keys()))
            stock_data = {}
            with Pool(cpu_count()) as pool:
                results = pool.map(process_stock, current_stocks)
            for symboltoken, df, _, _ in results:
                if df is not None:
                    stock_data[symboltoken] = df
            stock_data = stock_selection_filter(stock_data)
            for token in stock_data.keys():
                if token not in signals:
                    signals[token] = None
                if token not in buy_details_dict:
                    buy_details_dict[token] = None
        for symboltoken in current_stocks:
            df = stock_data.get(symboltoken)
            if df is None:
                continue
            last_signal = signals.get(symboltoken)
            buy_details = buy_details_dict.get(symboltoken)
            new_signal, new_buy_details, portfolio_balance, delivery_balance = check_signals(
                df, start_datetime, last_signal, portfolio_balance, delivery_balance, symboltoken, buy_details
            )
            signals[symboltoken] = new_signal
            buy_details_dict[symboltoken] = new_buy_details
            if new_signal == "delivery" and new_buy_details is not None:
                delivery_stocks[symboltoken] = new_buy_details
            elif symboltoken in delivery_stocks and new_signal != "delivery":
                delivery_stocks.pop(symboltoken, None)
        start_datetime += pd.Timedelta(minutes=1)
    total_events = profit_count + loss_count + no_trade_count
    if total_events > 0:
        profit_pct = (profit_count / total_events) * 100
        loss_pct = (loss_count / total_events) * 100
        delivery_pct = (delivery_count / total_events) * 100
        no_trade_pct = (no_trade_count / total_events) * 100
    else:
        profit_pct = loss_pct = delivery_pct = no_trade_pct = 0
    summary_str = (
        f"Final portfolio balance: {portfolio_balance:.2f}\n"
        f"Final delivery balance: {delivery_balance:.2f}\n"
        f"Profit trades: {profit_count} ({profit_pct:.2f}%)\n"
        f"Loss trades: {loss_count} ({loss_pct:.2f}%)\n"
        f"Delivery trades: {delivery_count} ({delivery_pct:.2f}%)\n"
        f"No trade events: {no_trade_count} ({no_trade_pct:.2f}%)\n"
    )
    print(summary_str)
    with open("trade_stats.txt", "w") as stats_file:
        stats_file.write(summary_str)

if __name__ == "__main__":
    main()