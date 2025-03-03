import requests
from bs4 import BeautifulSoup as bs
import datetime
import json
from playwright.sync_api import sync_playwright

def run():
    global third_column_data
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://chartink.com/screener/himanshumukanestockscreener")
        page.click('button[refs="run_scan"]')
        page.wait_for_selector("#DataTables_Table_0")
        stocks = page.locator("#DataTables_Table_0 tbody tr td:nth-child(3)").all_text_contents()
        col_7_values = page.locator("#DataTables_Table_0 tbody tr td:nth-child(7)").all_text_contents()
        col_7_values = [float(val.replace(",", "")) for val in col_7_values]
        sorted_data = sorted(zip(stocks, col_7_values), key=lambda x: x[1], reverse=True)
        third_column_data = [stock for stock, _ in sorted_data]
        browser.close()
        return third_column_data

def backtest_data():
    url = 'https://chartink.com/backtest/process'
    condition = {
        "scan_clause": "( {cash} ( latest rsi( 9 ) > 70 and latest volume > 50000 and latest close >= 200 and latest close <= 5000 and latest close - 1 candle ago close / 1 candle ago close * 100 >= 0.02 ) ) "
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
    current_date = datetime.datetime(2025, 3, 3)
    previous_days = []
    for record in final_data:
        record_date = datetime.datetime.strptime(record["Date"], "%Y-%m-%d")
        if record_date < current_date:
            previous_days.append((record_date, record))
    if previous_days:
        previous_record = max(previous_days, key=lambda x: x[0])[1]
        with open("previous_stock_data.json", "w") as f:
            json.dump(previous_record, f, indent=4)
    else:
        print("No trading data available for a day before", current_date.strftime("%Y-%m-%d"))
    return previous_record

def get_new_stocks():
    third_column_data = run()
    previous_record = backtest_data()
    result = [item for item in third_column_data if item not in previous_record["Stock"]]
    print( result)
    return result

get_new_stocks()