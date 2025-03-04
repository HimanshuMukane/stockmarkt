import requests
import json
from bs4 import BeautifulSoup as bs
import pandas as pd
import datetime
content = "FZJ4hJyY6uXw2bkrioEqQkjR1Lq418Bd5ckIbuz3"

url = 'https://chartink.com/backtest/process'

condition = {"scan_clause" : "( {cash} ( latest rsi( 9 ) > 60 and latest ema( latest close , 3 ) > weekly ema( weekly close , 3 ) and latest wma( latest close , 21 ) > weekly wma( weekly close , 21 ) and latest volume > 10000 and latest close >= 300 and latest close <= 5000 and latest close - 1 candle ago close / 1 candle ago close * 100 >= 0.02 ) ) "}

with requests.session() as s:
    r_data = s.get("https://chartink.com/screener/process")
    soup = bs(r_data.content, 'lxml')
    meta = soup.find('meta', {'name': 'csrf-token'})['content']
    headers = {"x-csrf-token": meta}
    data = s.post(url, data=condition, headers=headers).json()
    date = data["metaData"][0]["tradeTimes"]
    stock = data["aggregatedStockList"]
    final_data = []
    for i in range(0, len(date)):
        stk = []
        if stock[i] != []:
            for j in range(len(stock[i])):
                if j%3 == 0:
                    stk.append(stock[i][j])
            final_data.append(
                {
                    "Date": datetime.datetime.fromtimestamp(date[i]/1000),
                    "Stock": stk
                }
            )
        

# Define your target date
target_date = datetime.datetime(2025, 2, 27)

# Method 1: Using a for loop
stocks_for_date = None
for record in final_data:
    # Compare only the date part in case the time parts differ
    if record['Date'].date() == target_date.date():
        stocks_for_date = record['Stock']
        break

if stocks_for_date is not None:
    print("Stocks for", target_date.strftime("%Y-%m-%d"), ":", stocks_for_date)
else:
    print("No stock data found for", target_date.strftime("%Y-%m-%d"))
