# test_api.py
import requests

url = "https://xyzcheats.com/api/reseller_v1.php"
data = {
    'api_key': 'b25eb076f5c0412fa9f1eba94550d02e',
    'action': 'buy',
    'product_id': '133',
    'duration': '1 Day'
}
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'x-master-key': 'a7f3e8b2c9d1f4a6b8c2d5e9f1a3b6c8'
}

try:
    r = requests.post(url, data=data, headers=headers, timeout=30)
    print("=" * 50)
    print("STATUS CODE:", r.status_code)
    print("=" * 50)
    print("RESPONSE TEXT:")
    print(r.text)
    print("=" * 50)
    
    # Try to parse JSON
    try:
        import json
        result = json.loads(r.text)
        print("JSON PARSED:")
        print(json.dumps(result, indent=2))
    except:
        print("Not valid JSON")
        
except Exception as e:
    print("ERROR:", str(e))
