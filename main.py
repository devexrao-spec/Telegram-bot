# test_api_durations.py
import requests

url = "https://xyzcheats.com/api/reseller_v1.php"
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'x-master-key': 'a7f3e8b2c9d1f4a6b8c2d5e9f1a3b6c8'
}

# Try different duration formats
durations = [
    "1 Day",
    "1 Days",
    "1 DaYS",
    "1 DaYS NONROOT",
    "1D",
    "1 Day NONROOT",
    "1d",
    "1 Day Non-Root"
]

for duration in durations:
    data = {
        'api_key': 'b25eb076f5c0412fa9f1eba94550d02e',
        'action': 'buy',
        'product_id': '62',
        'duration': duration,
        'price': '32',
        'amount': '100'
    }
    
    r = requests.post(url, data=data, headers=headers, timeout=30)
    print(f"Duration: {duration}")
    print(f"Response: {r.text[:100]}")
    print("-" * 40)
    
    if 'success' in r.text:
        print("✅ FOUND WORKING DURATION!")
        break
