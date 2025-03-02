from flask import Flask, render_template, jsonify
import threading
import time
from stockmarkt import TradingBot

app = Flask(__name__)
trading_bot = TradingBot()

def run_trading_bot():
    while True:
        trading_bot.run()
        time.sleep(60)  # Run every minute

@app.route('/')
def index():
    stats = trading_bot.get_stats()
    return render_template('index.html', stats=stats)

@app.route('/api/stats')
def api_stats():
    return jsonify(trading_bot.get_stats())

if __name__ == '__main__':
    trading_thread = threading.Thread(target=run_trading_bot, daemon=True)
    trading_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True)
