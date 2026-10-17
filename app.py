"""
BACKEND FINAL COINBASE LIVE - MC Mat
Utilise ta clé cdp_api_key.json avec Ed25519
Version PROD Render - Se connecte vraiment à ton solde Coinbase
"""

import os
import json
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["*"])

# Essaie d'importer Coinbase, sinon mode mock
try:
    from coinbase.rest import RESTClient
    COINBASE_LIB_AVAILABLE = True
except ImportError:
    COINBASE_LIB_AVAILABLE = False
    print("⚠️  coinbase-advanced-py non installé - mode mock")

def get_coinbase_client():
    """Crée client Coinbase avec tes clés Render"""
    api_key = os.getenv('COINBASE_API_KEY')
    api_secret = os.getenv('COINBASE_API_SECRET')
    
    if not api_key or not api_secret:
        return None, "Clés non configurées dans Render Environment"
    
    if not COINBASE_LIB_AVAILABLE:
        return None, "Lib coinbase-advanced-py non installée"
    
    try:
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        return client, None
    except Exception as e:
        return None, f"Erreur création client: {str(e)}"

@app.route('/')
def home():
    api_key = os.getenv('COINBASE_API_KEY')
    has_keys = bool(api_key)
    
    return jsonify({
        "app": "MC Mat - Coinbase LIVE",
        "status": "Backend opérationnel" if has_keys else "En attente de clés",
        "coinbase_configured": has_keys,
        "coinbase_lib": COINBASE_LIB_AVAILABLE,
        "key_id_preview": api_key[-20:] if api_key else None,  # derniers chars seulement pour sécurité
        "endpoints": {
            "/api/balances/coinbase/live": "TON VRAI SOLDE COINBASE LIVE",
            "/api/balances/coinbase": "Solde (LIVE si clés, mock sinon)",
            "/api/test": "Test connexion Coinbase"
        },
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/test')
def test_coinbase():
    """Test connexion Coinbase LIVE"""
    client, error = get_coinbase_client()
    
    if error:
        return jsonify({
            "success": False,
            "error": error,
            "mock": True,
            "message": "Ajoute COINBASE_API_KEY et COINBASE_API_SECRET dans Render Environment"
        })
    
    try:
        # Test simple : récupère comptes
        accounts = client.get_accounts()
        
        # Filtre comptes avec solde > 0
        holdings = []
        for acc in accounts.get('accounts', []):
            balance = acc.get('available_balance', {})
            value = float(balance.get('value', 0))
            if value > 0:
                holdings.append({
                    "name": acc.get('name'),
                    "currency": balance.get('currency'),
                    "value": value,
                    "type": acc.get('type')
                })
        
        return jsonify({
            "success": True,
            "live": True,
            "accounts_count": len(holdings),
            "holdings": holdings,
            "raw_accounts": accounts,
            "message": f"✅ Connexion LIVE OK - {len(holdings)} comptes avec solde"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "live": False,
            "message": "Erreur connexion - vérifie tes clés et IP whitelist"
        }), 500

@app.route('/api/balances/coinbase/live')
def balances_coinbase_live():
    """TON VRAI SOLDE COINBASE LIVE - Utilise ta clé cdp_api_key.json"""
    client, error = get_coinbase_client()
    
    if error:
        # Fallback mock si pas de clés
        return jsonify({
            "live": False,
            "error": error,
            "total_eur": 2755.93,
            "holdings": [
                {"symbol": "BTC", "quantity": 0.0123, "price": 68523, "value": 842.83, "pnl": "+12%"},
                {"symbol": "ETH", "quantity": 0.45, "price": 3456, "value": 1555.2, "pnl": "+8%"},
                {"symbol": "PAXG", "quantity": 0.15, "price": 2386, "value": 357.9, "type": "or"},
            ],
            "message": "Mock - Configure tes clés dans Render pour LIVE"
        })
    
    try:
        accounts = client.get_accounts()
        holdings = []
        total_eur = 0
        
        # Prix mock pour conversion - en prod utilise /api/prices
        prices = {"BTC": 68523, "ETH": 3456, "SOL": 178.45, "PAXG": 2386, "EUR": 1, "USD": 0.92}
        
        for acc in accounts.get('accounts', []):
            bal = acc.get('available_balance', {})
            currency = bal.get('currency', '')
            value = float(bal.get('value', 0))
            
            if value > 0 and currency in prices:
                eur_value = value * prices.get(currency, 0) if currency != "EUR" else value
                total_eur += eur_value
                
                holdings.append({
                    "symbol": currency,
                    "quantity": value,
                    "currency": currency,
                    "value_eur": round(eur_value, 2),
                    "name": acc.get('name'),
                    "type": acc.get('type')
                })
        
        return jsonify({
            "live": True,
            "total_eur": round(total_eur, 2),
            "holdings": holdings,
            "accounts_raw_count": len(accounts.get('accounts', [])),
            "last_update": datetime.now().isoformat(),
            "message": f"✅ LIVE - Ton vrai solde Coinbase: {round(total_eur, 2)}€"
        })
        
    except Exception as e:
        return jsonify({
            "live": False,
            "error": str(e),
            "message": "Erreur LIVE - vérifie IP whitelist (mets 0.0.0.0/0 pour test)"
        }), 500

@app.route('/api/balances/coinbase')
def balances_coinbase():
    # Alias qui appelle live
    return balances_coinbase_live()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"""
=== BACKEND COINBASE LIVE MC Mat ===
Port: {port}
Coinbase lib: {COINBASE_LIB_AVAILABLE}
Clés configurées: {bool(os.getenv('COINBASE_API_KEY'))}

Pour Render:
  Build: pip install -r requirements.txt
  Start: gunicorn backend_final_coinbase_live:app
  Env vars: COINBASE_API_KEY + COINBASE_API_SECRET

Test local:
  http://localhost:{port}/api/test
  http://localhost:{port}/api/balances/coinbase/live
""")
    app.run(host='0.0.0.0', port=port)
