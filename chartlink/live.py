import requests
import json

# URL for the API endpoint
url = "https://chartink.com/oapi"

# Headers (include more headers if required)
headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
}

# Payload data; note the extra space before "where"
payload = {
    "query": "select open, high, low, close, volume, Close as 'indicatorsetid1layerIdaedbe207-036b-44f4-9f7e-91954db6bd21',filternumber({scan-link-null}) as 'indicatorsetid1layerIdaedbe207-036b-44f4-9f7e-91954db6bd21-color' where symbol='TEAMLEASE'",
    "use_live": "1",
    "limit": "1",
    "size": "200",
    "widget_id": "-1",
    "end_time": "-1",
    "timeframe": "1 minute",
    "symbol": "TEAMLEASE",
    "scan_link": "null"
}

# Send the POST request
response = requests.post(url, headers=headers, data=payload)

# Check if the request was successful
if response.status_code == 200:
    try:
        # Parse the JSON response
        data = response.json()
        
        # Save the data to a JSON file
        with open("data.json", "w") as f:
            json.dump(data, f, indent=4)
        print("Data saved to data.json")
    except json.JSONDecodeError:
        print("Error: Response is not in JSON format.")
else:
    print("Error: Received status code", response.status_code)
