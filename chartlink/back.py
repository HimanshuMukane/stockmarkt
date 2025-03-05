import requests
from bs4 import BeautifulSoup as bs
import datetime
import json
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