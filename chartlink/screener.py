import requests
import json
from bs4 import BeautifulSoup as bs
import pandas as pd

content = "FZJ4hJyY6uXw2bkrioEqQkjR1Lq418Bd5ckIbuz3"

url = 'https://chartink.com/screener/process'

condition = {
    "scan_clause": "( {cash} ( latest rsi( 9 ) > 70 and latest volume > 50000 and latest close >= 200 and latest close <= 5000 and latest close - 1 candle ago close / 1 candle ago close * 100 >= 0.02 ) ) "
}
with requests.session() as s:
    r_data = s.get(url)
    soup = bs(r_data.content, 'lxml')
    meta = soup.find('meta', {'name': 'csrf-token'})['content']
    headers = {"x-csrf-token": meta}
    data = s.post(url, data=condition, headers=headers).json()
    stock_List = pd.DataFrame(data['data'])
    nse_list = stock_List['nsecode'].tolist()
    print(nse_list)