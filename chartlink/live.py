import requests
import json

# Define the URL
url = "https://chartink.com/oapi"

# Define the headers
headers = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://chartink.com",
    "pragma": "no-cache",
    "referer": "https://chartink.com/stocks-new",
    "sec-ch-ua": '"Not(A:Brand";v="99", "Brave";v="133", "Chromium";v="133"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-gpc": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "x-xsrf-token": "eyJpdiI6IjNEdndLMFJSVnNOTDJHa0RsK095VWc9PSIsInZhbHVlIjoiVUdjdzlmSkxoYkJMMjJzRnVqeXpWajlvM2QxMTFkQWRZYmljNXZ5ZGJINkI1aCt4ZzdjdFRHT3FoUXZ2NHg0dGxKa3ZMU1VjN3haQjNXQUNRL0V0WVRrQU1uMGJ3dFpuNVoySlNHV1lSazR0dkRvaktjNDBqYTdGbDNua3MrRzkiLCJtYWMiOiIxOTljMWViNzE1MzNmMDMzMjdmMmQ3MzRhZGZiNmQ3MzM1MGI0NTc5YzEyZTYzNjY3MjU2NWQ3YjllOGUyMWQwIiwidGFnIjoiIn0="
}

# Define the payload data. Note that a space was added before "where" in the query.
data = {
    "query": "select open, high, low, close, volume , Close as 'indicatorsetid1layerId7ebde0c5-276b-43c8-8e34-77c12af895d0',filternumber({scan-link-null}) as 'indicatorsetid1layerId7ebde0c5-276b-43c8-8e34-77c12af895d0-color' where symbol='HOMEFIRST'",
    "use_live": "1",
    "limit": "1",
    "size": "245",
    "widget_id": "-1",
    "end_time": "-1",
    "timeframe": "1 minute",
    "symbol": "HOMEFIRST",
    "scan_link": "null"
}

# Send the POST request
response = requests.post(url, headers=headers, data=data)

# Check if the request was successful and save the JSON data to a file
if response.status_code == 200:
    try:
        response_data = response.json()
        with open("data.json", "w") as json_file:
            json.dump(response_data, json_file, indent=4)
        print("Data saved successfully to data.json")
    except json.JSONDecodeError:
        print("Response is not in valid JSON format.")
else:
    print(f"Request failed with status code {response.status_code}")
