from binance.client import Client

# Replace with your new Testnet API keys
API_KEY = "        "
API_SECRET = "    "

# Create client (Testnet Futures)
client = Client(API_KEY, API_SECRET, testnet=True)

try:
    # Test connectivity
    print("Server time:", client.futures_ping())
    
    # Check account balance
    balances = client.futures_account_balance()
    print("Balances:", balances)

    print("✅ API key is working!")
except Exception as e:
    print("❌ Error:", e)
