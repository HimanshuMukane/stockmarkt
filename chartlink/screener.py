import requests
import json
from bs4 import BeautifulSoup as bs
import pandas as pd

def get_screener_data():
    content = "FZJ4hJyY6uXw2bkrioEqQkjR1Lq418Bd5ckIbuz3"

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
        print(nse_list)
        print(len(nse_list))
        