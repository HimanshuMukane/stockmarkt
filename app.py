from flask import Flask, render_template, request
from chartlink.backtest import get_new_stocks
from automation import login_to_angel_one, livetest_data, process_stock, stock_selection_filter
import json
app = Flask(__name__)

JWT_TOKEN = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/changeToken', methods=['POST'])
def changeToken():
    global JWT_TOKEN
    totp = request.json.get('totp')
    res = login_to_angel_one(totp)
    if res.get('status') == 'success':
        JWT_TOKEN = res.get('data').get('jwtToken')
        stock_list = livetest_data()
        with open('stockList.json', 'r') as file:
            stock_data = json.load(file)
            name_to_token = {entry["name"]: entry["token"] for entry in stock_data}
            global token_to_name
            token_to_name = {entry["token"]: entry["name"] for entry in stock_data}        
        stock_data = {}
        for stock in stock_list:
            symboltoken, df = process_stock(JWT_TOKEN, stock)
            if df is not None:
                stock_data[symboltoken] = df
        selected_stocks = stock_selection_filter(stock_data)

        # goes to historical data to be searched
        # result will be send to
        # Historical
        # EMA 9 and 21
        # Supertrend
        # buy sell
        # transaction charges
        return {'status': 'success', 'message': 'Token Changed Successfully'}
    return res

print(get_new_stocks())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

