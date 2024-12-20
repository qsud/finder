import requests
import json
import asyncio
import telebot
import threading
from flask import Flask
import time
import logging

app = Flask('')

@app.route('/')
def home():
    return "I am alive"

def run_flask():
    try:
        app.run(host='0.0.0.0', port=8085)
    except Exception as e:
        logging.error(f"Error in Flask server: {e}")

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.start()

rpc_url = "https://mainnet.helius-rpc.com/?api-key=3306ede2-b0da-4ea3-a571-50369811ddb4"

exchange_wallets = [
    "A77HErqtfN1hLLpvZ9pCtu66FEtM8BveoaKbbMoZ4RiR",
    "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9",
    "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm",
    "BmFdpraQhkiDQE6SnfG5omcA1VwzqfXrwtNYBwWTymy6",
    "5VCwKtCXgCJ6kit5FybXjvriW3xELsFDhYrPSqtJNmcD",
    "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2",
]

telegram_bot_token = "7738255372:AAF0YkZkcsUHfGDVxzAzMXGFg9a_bFanKjM"
telegram_user_id = "-1002415943593"
bot = telebot.TeleBot(telegram_bot_token)

def get_signatures_for_address(pubkey, limit=5):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [pubkey, {"limit": limit}],
    }
    response = requests.post(rpc_url, json=payload)
    return response.json()

def get_transaction(signature):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [signature, {"maxSupportedTransactionVersion": 0}],
    }
    response = requests.post(rpc_url, json=payload)
    return response.json()

def get_token_metadata(token_address):
    return {"market_cap": "Unknown"}

def get_transaction_count(pubkey):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [pubkey, {"limit": 50000}],
    }
    response = requests.post(rpc_url, json=payload)
    if response.status_code == 200 and "result" in response.json():
        return len(response.json()["result"])
    return 0

def parse_transaction_for_amount(transaction):
    if "meta" in transaction and "postBalances" in transaction["meta"] and "preBalances" in transaction["meta"]:
        pre_balances = transaction["meta"]["preBalances"]
        post_balances = transaction["meta"]["postBalances"]
        for pre, post in zip(pre_balances, post_balances):
            change = abs(pre - post) / (10 ** 9)
            if change > 0:
                return change
    return 0

async def monitor_wallets():
    processed_signatures = set()
    processed_wallets = set()

    while True:
        for wallet in exchange_wallets:
            signatures_response = get_signatures_for_address(wallet)
            if "result" not in signatures_response or len(signatures_response["result"]) == 0:
                continue

            for signature_info in signatures_response["result"]:
                signature = signature_info["signature"]

                if signature in processed_signatures:
                    continue
                processed_signatures.add(signature)

                transaction_response = get_transaction(signature)
                if "result" not in transaction_response or not transaction_response["result"]:
                    continue

                transaction = transaction_response["result"]
                amount = parse_transaction_for_amount(transaction)
                if amount > 100:
                    account_keys = transaction["transaction"]["message"]["accountKeys"]
                    for account in account_keys[1:]:
                        if account not in processed_wallets:
                            processed_wallets.add(account)
                            tx_count = get_transaction_count(account)
                            if tx_count < 50000:
                                print(f"New wallet detected with < 100 transactions: {account}")
                                bot.send_message(chat_id=telegram_user_id, text=account)

        await asyncio.sleep(10)

def start_bot_polling():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Error in bot polling: {e}")
            time.sleep(5)

if __name__ == "__main__":
    keep_alive()  # Start the Flask server
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, start_bot_polling)  # Run bot polling in a separate thread
    loop.run_until_complete(monitor_wallets())  # Monitor wallets concurrently
