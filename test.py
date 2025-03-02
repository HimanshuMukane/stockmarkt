import datetime
import time
import http.client
import pandas as pd
import json
import numpy as np
from numpy import nan as npNaN
import pandas_ta as ta
from warnings import filterwarnings
import pytz  # Added import
import logging

# Configure logging: logs will be output to both console and log.txt
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("log.txt"),
              logging.StreamHandler()])

filterwarnings('ignore')

API_URL = "apiconnect.angelone.in"
HEADERS = {
    'Accept': 'application/json',
    'X-UserType': 'USER',
    'X-SourceID': 'WEB',
    'X-ClientLocalIP': 'CLIENT_LOCAL_IP',
    'X-ClientPublicIP': 'CLIENT_PUBLIC_IP',
    'X-MACAddress': 'MAC_ADDRESS',
    'X-PrivateKey': 'pqZKC285'
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


def supertrend(df, atr_multiplier):
    # Calculate ATR and drop rows with NaN values.
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], period=10)
    df.dropna(inplace=True)

    # Check if there's enough data to proceed.
    if df.empty:
        logging.warning(
            "Dataframe is empty after calculating ATR in supertrend.")
        return df

    # Recalculate the average using the cleaned dataframe.
    current_avg = (df['high'] + df['low']) / 2
    df['basicUpperband'] = current_avg + (atr_multiplier * df['atr'])
    df['basicLowerband'] = current_avg - (atr_multiplier * df['atr'])

    # Use the first row to initialize upper and lower bands.
    first_upper = df['basicUpperband'].iloc[0]
    first_lower = df['basicLowerband'].iloc[0]
    upperBand = [first_upper]
    lowerBand = [first_lower]

    for i in range(1, len(df)):
        if df['basicUpperband'].iloc[i] < upperBand[i - 1] or df['close'].iloc[
                i - 1] > upperBand[i - 1]:
            upperBand.append(df['basicUpperband'].iloc[i])
        else:
            upperBand.append(upperBand[i - 1])

        if df['basicLowerband'].iloc[i] > lowerBand[i - 1] or df['close'].iloc[
                i - 1] < lowerBand[i - 1]:
            lowerBand.append(df['basicLowerband'].iloc[i])
        else:
            lowerBand.append(lowerBand[i - 1])

    df['upperband'] = upperBand
    df['lowerband'] = lowerBand
    df.drop(['basicUpperband', 'basicLowerband'], axis=1, inplace=True)
    return df


def calculate_supertrend_indicator(df):
    supertrend_vals = []
    for i in range(len(df)):
        if df['close'].iloc[i] > df['upperband'].iloc[i]:
            supertrend_vals.append("Green")
        elif df['close'].iloc[i] < df['lowerband'].iloc[i]:
            supertrend_vals.append("Red")
        else:
            if i == 0:
                supertrend_vals.append("Green")
            else:
                supertrend_vals.append(supertrend_vals[-1])
    df['Supertrend'] = supertrend_vals
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


def get_historical_data(auth_token, symboltoken):
    ist = pytz.timezone('Asia/Kolkata')  # Define IST timezone
    now = datetime.datetime.now(ist)  # Current time in IST
    from_date = now.replace(hour=9, minute=14, second=0, microsecond=0)
    if now.hour < 15 or (now.hour == 15 and now.minute < 30):
        to_date = now
    else:
        to_date = now.replace(hour=15, minute=30, second=0, microsecond=0)

    payload = {
        "exchange": "NSE",
        "symboltoken": symboltoken,
        "interval": "ONE_MINUTE",
        "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
        "todate": to_date.strftime("%Y-%m-%d %H:%M")
    }
    response = make_request(
        "POST", "/rest/secure/angelbroking/historical/v1/getCandleData",
        payload, auth_token)
    return response


def check_signals(df,
                  user_datetime,
                  last_signal,
                  portfolio_balance,
                  symboltoken,
                  buy_details=None):
    # Remove timezone localization since user_datetime is already in correct tz
    window_start = user_datetime - pd.Timedelta(minutes=1)
    df_filtered = df.loc[window_start:user_datetime]

    for i in range(1, len(df_filtered)):
        current_close = df_filtered['close'].iloc[i]
        current_supertrend = df_filtered['Supertrend'].iloc[i]
        current_ema50 = df_filtered['EMA50'].iloc[i]
        # Check for buy signal
        if last_signal != "buy" and portfolio_balance > 0:
            if (df_filtered['EMA9'].iloc[i - 1]
                    <= df_filtered['EMA21'].iloc[i - 1] and
                    df_filtered['EMA9'].iloc[i] > df_filtered['EMA21'].iloc[i]
                    and user_datetime.time() < datetime.time(
                        13, 5)):  # Use datetime.time for comparison
                if current_supertrend == "Green" and current_ema50 <= current_close:
                    shares_to_buy = int(portfolio_balance // current_close)
                    if shares_to_buy > 0:
                        cost = shares_to_buy * current_close
                        portfolio_balance -= cost
                        buy_details = (current_close, shares_to_buy)
                        logging.info(
                            f"Buy Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {shares_to_buy} of {symboltoken}"
                        )
                        return "buy", buy_details, portfolio_balance
            if user_datetime.time() < datetime.time(10, 0): # 10 am
                condition_met = all(
                    df_filtered['EMA9'].iloc[j - 1] <= df_filtered['EMA21'].iloc[j - 1] and
                    df_filtered['EMA9'].iloc[j] > df_filtered['EMA21'].iloc[j]
                    for j in range(i - 10, i)
                )
                if condition_met and current_supertrend == "Green":
                    shares_to_buy = int(portfolio_balance // current_close)
                    if shares_to_buy > 0:
                        cost = shares_to_buy * current_close
                        portfolio_balance -= cost
                        buy_details = (current_close, shares_to_buy)
                        logging.info(
                            f"Buy Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {shares_to_buy} of {symboltoken}"
                        )
                        return "buy", buy_details, portfolio_balance
        if last_signal == "buy" and buy_details is not None:
            if (df_filtered['EMA9'].iloc[i - 1]
                    >= df_filtered['EMA21'].iloc[i - 1]
                    and df_filtered['EMA9'].iloc[i]
                    < df_filtered['EMA21'].iloc[i]):
                if current_supertrend == "Red" and current_ema50 >= current_close and current_close >= buy_details[
                        0]:
                    proceeds = buy_details[1] * current_close
                    portfolio_balance += proceeds
                    logging.info(
                        f"Sell Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken} (Profit from Buy)"
                    )
                    return "sell", None, portfolio_balance
            if buy_details[0] <= current_close * 0.975:
                proceeds = buy_details[1] * current_close
                portfolio_balance += proceeds
                logging.info(
                    f"Sell Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken} (Early Profit from Buy)"
                )
                return "sell", None, portfolio_balance
            if datetime.time(14, 50) < user_datetime.time() < datetime.time(
                    15, 55):  # Use datetime.time
                proceeds = buy_details[1] * current_close
                if current_close < buy_details[0]:
                    logging.info(
                        f"Sell Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken} (Loss from Buy)"
                    )
                else:
                    logging.info(
                        f"Sell Signal at {df_filtered.index[i]} - Price: {current_close:.2f}, Shares: {buy_details[1]} of {symboltoken} (Profit from Buy)"
                    )
                portfolio_balance += proceeds
                return "sell", None, portfolio_balance
    return last_signal, buy_details, portfolio_balance


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
        daily['MA5'] = daily['close'].rolling(window=3).mean()
        last3 = daily.iloc[-3:]
        if (last3['close'] < (last3['MA5'] * 0.98)).all():
            logging.info(
                f"Excluding stock {token}: Last 3 days' close prices are below 90% of the 5-day moving average."
            )
        else:
            selected_stocks[token] = df
    return selected_stocks


def main():
    client_id = "H88522"
    client_pin = "4542"
    totp = "2885"
    # refresh_token = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VybmFtZSI6Ikg4ODUyMiIsInJvbGVzIjowLCJ1c2VydHlwZSI6IlVTRVIiLCJ0b2tlbiI6ImV5SmhiR2NpT2lKU1V6STFOaUlzSW5SNWNDSTZJa3BYVkNKOS5leUoxYzJWeVgzUjVjR1VpT2lKamJHbGxiblFpTENKMGIydGxibDkwZVhCbElqb2lkSEpoWkdWZllXTmpaWE56WDNSdmEyVnVJaXdpWjIxZmFXUWlPallzSW5OdmRYSmpaU0k2SWpNaUxDSmtaWFpwWTJWZmFXUWlPaUl4TkRFMk9XWTBNQzFtWmpVekxUTTFNekF0WWpnM1ppMDBPVGhsWXpjME5XVmpORFlpTENKcmFXUWlPaUowY21Ga1pWOXJaWGxmZGpFaUxDSnZiVzVsYldGdVlXZGxjbWxrSWpvMkxDSndjbTlrZFdOMGN5STZleUprWlcxaGRDSTZleUp6ZEdGMGRYTWlPaUpoWTNScGRtVWlmU3dpYldZaU9uc2ljM1JoZEhWeklqb2lZV04wYVhabEluMTlMQ0pwYzNNaU9pSjBjbUZrWlY5c2IyZHBibDl6WlhKMmFXTmxJaXdpYzNWaUlqb2lTRGc0TlRJeUlpd2laWGh3SWpveE56UXdOVFF4TXpRMExDSnVZbVlpT2pFM05EQTBOVFEzTmpRc0ltbGhkQ0k2TVRjME1EUTFORGMyTkN3aWFuUnBJam9pTkRCaVpqUTVNell0TURsbVlTMDBabUZrTFdFeE9UVXRORE01TldJNE9XUXhOemxrSWl3aVZHOXJaVzRpT2lJaWZRLlNlRVMwa2F5ZXNhVFRQTXRXZHpaTVJnM1pZQVBHNkFnb3pLVTZlazdYSnBVT3J1cW1EUmw5djJXOHJpdHNCSE5nNzhfTll4QlhlSTh6RWszMHdDV0dsRkQ1M01oeG51eHFfT3Y5QUlUR3lQMHlQQzBwOHFMR19HdXlHc3FCRkVqc1ZSVVgzcWNYTF9fRWlVa2NWeXVNTV9LamVQNXFaZmMyR0FIVVBSc3VQOCIsIkFQSS1LRVkiOiJiSEpNeVdrVCIsImlhdCI6MTc0MDQ1NDk0NCwiZXhwIjoxNzQwNTQxMzQ0fQ.LhzjDyAXIxIi2nwcumipkWq0L9xFlU-gp3II-9Y8w7SVmpI-zJqDoVHn_v3Ns1OVTZiH2lqAui_rwy9fyegBAg"
    auth_token = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VybmFtZSI6Ikg4ODUyMiIsInJvbGVzIjowLCJ1c2VydHlwZSI6IlVTRVIiLCJ0b2tlbiI6ImV5SmhiR2NpT2lKU1V6STFOaUlzSW5SNWNDSTZJa3BYVkNKOS5leUoxYzJWeVgzUjVjR1VpT2lKamJHbGxiblFpTENKMGIydGxibDkwZVhCbElqb2lkSEpoWkdWZllXTmpaWE56WDNSdmEyVnVJaXdpWjIxZmFXUWlPallzSW5OdmRYSmpaU0k2SWpNaUxDSmtaWFpwWTJWZmFXUWlPaUl3TkRrek1XTmlZeTB3WkRFeExUTmpNelF0WWpOaU5DMDNOakk0TWprMlpEa3hZV0lpTENKcmFXUWlPaUowY21Ga1pWOXJaWGxmZGpJaUxDSnZiVzVsYldGdVlXZGxjbWxrSWpvMkxDSndjbTlrZFdOMGN5STZleUprWlcxaGRDSTZleUp6ZEdGMGRYTWlPaUpoWTNScGRtVWlmU3dpYldZaU9uc2ljM1JoZEhWeklqb2lZV04wYVhabEluMTlMQ0pwYzNNaU9pSjBjbUZrWlY5c2IyZHBibDl6WlhKMmFXTmxJaXdpYzNWaUlqb2lTRGc0TlRJeUlpd2laWGh3SWpveE56UXhNREkzTWpJekxDSnVZbVlpT2pFM05EQTVOREEyTkRNc0ltbGhkQ0k2TVRjME1EazBNRFkwTXl3aWFuUnBJam9pTm1Ga01tSXlaR0V0TUdWbU9DMDBOREpqTFdFNE9UTXRNV1F5TmpObE5UQTVOR1poSWl3aVZHOXJaVzRpT2lJaWZRLm9TREdFSC1IZG0zc25YQkMzcEhoR1A1MFhna204SkZjdEV3bnpBbVhiTzJVZE1VN0x4bWkwdXg5U1J0blZSTmt5amNPaG5ZRjg3WnlieWkzTjZVOFd5Nmd6V2FubWlVTDQ3TUdBbFNybU93dE0wV3N6SGhXdWZqdEhFbnJFRDVnVVdzczQ1NlR6dDJXdkczYXcxZk9BWFRud2tUUlJjQ3J4X0pnR3ZVekFnNCIsIkFQSS1LRVkiOiJwcVpLQzI4NSIsImlhdCI6MTc0MDk0MDgyMywiZXhwIjoxNzQxMDI3MjIzfQ.ttnLNIOgfD96cymuZO1kRUEXlBbU8VeqhrTdUAdj8CnHbXmUZHKUxotsQcx8QlSWgmTqZcQmvXj3Q0kRAkfGZg"

    stocks = ['16713', '18284', '19686', '4306', '7936']
    signals = {symbol: None for symbol in stocks}
    buy_details_dict = {symbol: None for symbol in stocks}
    portfolio_balance = 20000
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    while True:
        try:
            stock_data = {}
            for symboltoken in stocks:
                json_str = get_historical_data(auth_token, symboltoken)
                time.sleep(3)
                # print(json_str)
                # logging.info(json_str)
                if not json_str:
                    logging.info(
                        f"Empty response for symbol {symboltoken}. Check API and credentials."
                    )
                    continue
                try:
                    data_json = json.loads(json_str)
                except json.decoder.JSONDecodeError as e:
                    logging.info(
                        f"Error decoding JSON for symbol {symboltoken}: {e}")
                    continue

                df = pd.DataFrame(data_json['data'], columns=cols)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                df = df.between_time('09:15', '15:30')  # Times in IST

                if df.empty:
                    logging.warning(
                        f"No data available for symbol {symboltoken} after time filtering."
                    )
                    continue

                df['EMA9'] = df['close'].ewm(span=7, adjust=False).mean()
                df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
                df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()

                df = supertrend(df, atr_multiplier=6)
                if df.empty:
                    logging.warning(
                        f"Not enough data to calculate supertrend for symbol {symboltoken}."
                    )
                    continue

                df = calculate_supertrend_indicator(df)
                stock_data[symboltoken] = df

            stock_data = stock_selection_filter(stock_data)

            current_datetime = pd.Timestamp.now(
                tz='Asia/Kolkata')  # Get current time in IST
            logging.info(f"Current datetime: {current_datetime}")
            for symboltoken in stocks:
                if symboltoken not in stock_data:
                    continue
                df = stock_data[symboltoken]
                last_signal = signals[symboltoken]
                buy_details = buy_details_dict[symboltoken]

                new_signal, new_buy_details, portfolio_balance = check_signals(
                    df, current_datetime, last_signal, portfolio_balance,
                    symboltoken, buy_details)
                signals[symboltoken] = new_signal
                buy_details_dict[symboltoken] = new_buy_details

            time.sleep(2)
        except Exception as e:
            logging.error(f"Exception occurred: {e}", exc_info=True)
            time.sleep(1)

if __name__ == "__main__":
    main()