import requests
import json
from bs4 import BeautifulSoup as bs
import pandas as pd

content = "7GTZmPkuz52aWdNsRPXN1ZtjSaoN0Qg36l5CAabA"

url = 'https://chartink.com/screener/process'

condition = {"scan_clause" : "( {cash} ( latest rsi( 9 ) > 50 and latest volume > 2000 and latest close >= 300 and latest close <= 5000 ) ) "}

with requests.session() as s:
    r_data = s.get(url)
    soup = bs(r_data.content, 'lxml')
    meta = soup.find('meta', {'name': 'csrf-token'})['content']
    headers = {"x-csrf-token": meta}
    data = s.post(url, data=condition, headers=headers).json()
    stock_List = pd.DataFrame(data['data'])

    # Filter rows where per_chg >= 0.01
    stock_List = stock_List[stock_List['per_chg'] >= 0.01]

    # Sort by per_chg in descending order
    stock_List = stock_List.sort_values(by='per_chg', ascending=False)

    # Print the filtered and sorted DataFrame
    print(stock_List)