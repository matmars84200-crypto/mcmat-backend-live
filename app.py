import os
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["*"])

try:
    from coinbase.rest import RESTClient
    LIB = True
except:
    LIB = False

def get_client():
    api_key = os.getenv('COINBASE_API_KEY')
    api_secret = os.getenv('COINBASE_API_SECRET')
    
    if not api_key or not api_secret:
        return None, "Cles non configurees dans Render Environment"

    # FIX CRITIQUE RENDER : si tu as colle la cle sur une ligne avec \n texte
    # on le convertit en vrai saut de ligne
    if "\\n" in api_secret:
        api_secret = api_secret.replace("\\n", "\n")
    if "\\n" in api_secret:  # au cas ou double escape
        api_secret = api_secret.replace("\\n", "\n")

    try:
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        return client, None
    except Exception as e:
        return None, str(e)

@app.route('/')
def home():
    return jsonify({
        "app": "MC Mat - Coinbase LIVE",
        "coinbase_configured": bool(os.getenv('COINBASE_API_KEY')),
        "coinbase_lib": LIB,
        "endpoints": {
            "/api/test": "Test connexion",
            "/api/balances/coinbase/live": "VRAI SOLDE LIVE"
        }
    })

@app.route('/api/test')
def test():
    client, err = get_client()
    if err:
        return jsonify({"success": False, "error": err, "mock": True})
    try:
        accounts = client.get_accounts()
        holdings = []
        for a in accounts.get('accounts', []):
            bal = a.get('available_balance', {})
            v = float(bal.get('value', 0))
            if v > 0:
                holdings.append({"name": a.get('name'), "currency": bal.get('currency'), "value": v})
        return jsonify({"success": True, "live": True, "holdings": holdings, "message": "LIVE OK"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/balances/coinbase/live')
def live():
    client, err = get_client()
    if err:
        return jsonify({"live": False, "error": err, "total_eur": 0})
    try:
        accounts = client.get_accounts()
        holdings = []
        total = 0
        prices = {"BTC": 68523, "ETH": 3456, "SOL": 178.45, "PAXG": 2386, "EUR": 1, "USD": 0.92, "USDC": 0.92}
        for a in accounts.get('accounts', []):
            bal = a.get('available_balance', {})
            cur = bal.get('currency', '')
            v = float(bal.get('value', 0))
            if v > 0 and cur in prices:
                eur = v * prices.get(cur, 0) if cur != "EUR" else v
                total += eur
                holdings.append({"symbol": cur, "quantity": v, "value_eur": round(eur, 2)})
        return jsonify({"live": True, "total_eur": round(total, 2), "holdings": holdings})
    except Exception as e:
        return jsonify({"live": False, "error": str(e)}), 500

@app.route('/api/balances/coinbase')
def alias():
    return live()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
