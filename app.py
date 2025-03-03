from flask import Flask, render_template, request
from chartlink.backtest import get_new_stocks
import http.client
import json

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
CLIENT_ID = "H88522"
CLIENT_PIN = "4542"
STATE_VARIABLE = "live"

JWT_TOKEN = None

app = Flask(__name__)

def login_to_angel_one(totp):
    conn = http.client.HTTPSConnection(API_URL)
    payload = json.dumps({
        "clientcode": CLIENT_ID,
        "password": CLIENT_PIN,
        "totp": totp,
        "state": STATE_VARIABLE
    })
    
    headers = {**HEADERS, 'Content-Type': 'application/json'}
    conn.request("POST", "/rest/auth/angelbroking/user/v1/loginByPassword", payload, headers)

    res = conn.getresponse()
    data = res.read().decode("utf-8")
    return data


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/changeToken', methods=['POST'])
def changeToken():
    totp = request.json.get('totp')
    res = login_to_angel_one(totp)
    if res.get('status') == 'success':
        JWT_TOKEN = res.get('data').get('jwtToken')
        return {'status': 'success', 'message': 'Token Changed Successfully'}
    return res

print(get_new_stocks())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

