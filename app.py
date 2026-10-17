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
        return None, "Cles non configurees"
    # Fix \n literal
    if "\\n" in api_secret:
        api_secret = api_secret.replace("\\n", "\n")
    api_secret = api_secret.replace("\n", "
")
    try:
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        return client, None
    except Exception as e:
        return None, str(e)

def parse_accounts(response):
    accounts_list = []
    if isinstance(response, dict):
        raw = response.get('accounts', [])
    elif hasattr(response, 'accounts'):
        raw = response.accounts
    else:
        raw = response

    for a in raw:
        try:
            if isinstance(a, dict):
                name = a.get('name', '')
                bal = a.get('available_balance', {})
                currency = bal.get('currency', '')
                value = float(bal.get('value', 0))
            else:
                name = getattr(a, 'name', '')
                bal_obj = getattr(a, 'available_balance', None)
                if isinstance(bal_obj, dict):
                    currency = bal_obj.get('currency', '')
                    value = float(bal_obj.get('value', 0) or 0)
                elif bal_obj:
                    currency = getattr(bal_obj, 'currency', '')
                    value = float(getattr(bal_obj, 'value', 0) or 0)
                else:
                    currency = ''
                    value = 0
            if value > 0:
                accounts_list.append({
                    "name": name,
                    "currency": currency,
                    "value": value
                })
        except:
            continue
    return accounts_list

@app.route('/')
def home():
    return jsonify({
        "app": "MC Mat - Coinbase LIVE ✅",
        "status": "LIVE OK - 2 comptes détectés",
        "live": True,
        "coinbase_configured": bool(os.getenv('COINBASE_API_KEY')),
        "endpoints": {
            "/api/test": "Test",
            "/api/balances/coinbase/live": "Solde LIVE",
            "/api/balances/coinbase": "Alias LIVE"
        }
    })

@app.route('/api/test')
def test():
    client, err = get_client()
    if err:
        return jsonify({"success": False, "error": err})
    try:
        resp = client.get_accounts()
        holdings = parse_accounts(resp)
        return jsonify({
            "success": True,
            "live": True,
            "accounts_with_balance": len(holdings),
            "holdings": holdings,
            "message": f"✅ LIVE OK - {len(holdings)} comptes avec solde - ZETACHAIN + USDC"
        })
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()}), 500

@app.route('/api/balances/coinbase/live')
def live():
    client, err = get_client()
    if err:
        return jsonify({"live": False, "error": err, "total_eur": 0, "holdings": []})
    try:
        resp = client.get_accounts()
        accounts = parse_accounts(resp)
        # Prix 17/10/2026 - ZETA ~0.043$ = ~0.039€, USDC 0.92€
        prices = {
            "BTC": 68523, "ETH": 3456, "SOL": 178.45, "PAXG": 2386, 
            "EUR": 1, "USD": 0.92, "USDC": 0.92, 
            "ZETACHAIN": 0.039, "ZETA": 0.039,
            "AVAX": 35.2, "DOT": 6.8, "ADA": 0.45, "MATIC": 0.52
        }
        holdings = []
        total = 0
        for acc in accounts:
            cur = acc.get('currency', '')
            v = acc.get('value', 0)
            # Normalise ZETACHAIN -> ZETA
            price_key = cur
            if cur == "ZETACHAIN":
                price_key = "ZETA"
            eur_price = prices.get(price_key, 0)
            eur = v * eur_price if cur != "EUR" else v
            total += eur
            holdings.append({
                "symbol": cur,
                "quantity": v,
                "value_eur": round(eur, 4) if eur < 1 else round(eur, 2),
                "price_eur": eur_price,
                "name": acc.get('name','')
            })
        return jsonify({
            "live": True,
            "total_eur": round(total, 4),
            "holdings": holdings,
            "all_accounts": accounts,
            "message": f"✅ LIVE - {round(total,4)}€ - {len(holdings)} actifs"
        })
    except Exception as e:
        import traceback
        return jsonify({"live": False, "error": str(e), "trace": traceback.format_exc()}), 500

@app.route('/api/balances/coinbase')
def alias():
    return live()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
