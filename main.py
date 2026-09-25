import sys
from datetime import datetime, timezone

import requests
from bitcoinlib.encoding import EncodingError
from bitcoinlib.keys import Address
from rich.pretty import pprint

# https://mempool.space/api/address/1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv/txs

METHODS = ["Trace by Address", "Trace by UTXO"]

def is_valid_bitcoin_address(address):
    try:
        Address.parse(address)
        return True
    except EncodingError:
        return False
    
def fetch_transactions(address):
        url = f"https://mempool.space/api/address/{address}/txs"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    
def get_outgoing_outputs(transactions, address):
    outputs = []

    for trans in transactions:
        address_is_input = any(
            vin.get("prevout", {}).get("scriptpubkey_address") == address
            for vin in trans["vin"]
        )

        if not address_is_input:
            continue

        for output_index, out in enumerate(trans["vout"]):
            if out.get("scriptpubkey_address") == address:
                continue

            outputs.append({
                "txid": trans["txid"],
                "vout": output_index,
                "amount": out.get("value"),
                "address": out.get("scriptpubkey_address"),
                "time": trans["status"].get("block_time"),
            })

    return outputs

def fetch_transaction_by_txid(txid):
    url = f"https://mempool.space/api/tx/{txid}"

    response = requests.get(url)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def trace_by_address():
    user_input_address = input("Address:\n> ")

    if user_input_address == "test":
        address = "1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv"
        dt_original = datetime(2014, 5, 1, 0, 0, tzinfo=timezone.utc)
        amount_original = 13_370_000
        threshold = 15

    # Input Validation
    else:
        if not is_valid_bitcoin_address(user_input_address):
            print("Invalid Bitcoin address")
            sys.exit()

        address = user_input_address

        # INPUT Date/Time
        user_input_datetime = input("Date/Time (year month day hour minute) - UTC +0\n>")

        try:
            user_dt = [int(val) for val in user_input_datetime.split()]
            
            if len(user_dt) != 5:
                raise ValueError("Exactly 5 numbers are required")
            
            dt_original = datetime(
                user_dt[0], 
                user_dt[1], 
                user_dt[2], 
                user_dt[3], 
                user_dt[4], 
                tzinfo=timezone.utc)
        except ValueError:
            print("One of your values isn't valid")
            sys.exit()

        # INPUT AMOUNT
        try:
            amount_original = int(input("Target amount:\n>"))
            if amount_original <= 0:
                print("Target amount must be greater than 0")
                sys.exit()
        except ValueError:
            print("Entered target amount is not a valid number")
            sys.exit()
            
        # INPUT Threshold
        try:
            threshold = int(input("Target threshold:\n>"))
            if not 0 < threshold <= 100:
                print("Threshold should be between 1 and 100")
                sys.exit()
        except ValueError:
            print("Entered target threshold is not a valid number")
            sys.exit()



    dt_original_unix = int(dt_original.timestamp())

    amount_min = amount_original * (1 - threshold / 100)
    amount_max = amount_original * (1 + threshold / 100)
    
    
    visited = set()
    last_output = None

    while True:
        if address in visited:
            print("STOP: Address already visited")
            break

        visited.add(address)

        transactions = fetch_transactions(address)
        outputs = get_outgoing_outputs(transactions, address)

        filtered_date_outputs = [
            tx for tx in outputs
            if tx["time"] is not None
            and tx["time"] > dt_original_unix
        ]

        if not filtered_date_outputs:
            print("STOP: No outputs after the original date.")
            break

        closest_output = min(
            filtered_date_outputs,
            key=lambda tx: abs(tx["amount"] - amount_original)
        )

        if not amount_min <= closest_output["amount"] <= amount_max:
            print("STOP: Closest output is outside the set threshold")
            break

        if closest_output["address"] is None:
            print("STOP: Closest output has no address.")
            break

        last_output = closest_output
        address = closest_output["address"]

    return last_output

def trace_by_utxo():
    txid = input("TXID:\n> ")
    
    transaction = fetch_transaction_by_txid(txid)
    
    if transaction is None:
        print("Transaction not found.")
        return None

    try:
        vout = int(input("VOUT:\n> "))
        if vout < 0:
            print("VOUT cannot be negative.")
            return None
    except ValueError:
        print("VOUT must be a number.")
        return None

    try:
        threshold = int(input("Threshold (%):\n> "))
        if not 0 < threshold <= 100:
            print("Threshold should be between 1 and 100.")
            return None
    except ValueError:
        print("Threshold must be a number.")
        return None

    # UTXO tracing logic

    return f"tx: {transaction}\nvout: {vout}\nthrehold: {threshold}"
    

result = None



# INPUTS + VALIDATION

# Method
print("Choose Tracing-method:")

for idx, method in enumerate(METHODS, start=1):
    print(f"{idx}: {method}")

try:
    user_input_method = int(input("> "))

    if not 1 <= user_input_method <= len(METHODS):
        print("Invalid method/number.")
        sys.exit()

except ValueError:
    print("Invalid method/number.")
    sys.exit()

# Bitcoin-Adress / Test Case

if user_input_method == 1:
    result = trace_by_address()
    
elif user_input_method == 2:
    result = trace_by_utxo()


if result is None:
    print("No valid output matching the tracing criteria was found.")
else:
    pprint(result)





# Bitcoin address/amount tracing heuristic:

# 1. Get all transactions involving the current address. (SPENT AND RECIEVED -> thats just the API)
# 2. Check VIN: only keep transactions where the address actually spent funds. -> VIN = where SPENT funds came from
# 3. Check VOUT: these are the destinations of that transaction. -> VOUT: Where the funds are being SENT
# 4. Ignore outputs going back to the same address.
# 5. Only consider outputs after the original date.
# 6. Find the output closest to the ORIGINAL amount.
# 7. Accept it only if it is within the ORIGINAL threshold.
# 8. Continue tracing from the accepted output's address.
# 9. visited prevents loops / revisiting addresses.
# 10. last_output stores the last VALID output before the trace stops.

# Important:
# VOUT = transaction outputs, NOT automatically "outgoing from my address".
# VIN tells us whether the current address actually spent funds.
# Original amount/date/threshold stay FIXED during the entire trace.
# This is a heuristic: it suggests a path, it does not prove coin ownership/flow.

# ----------------



# Exact UTXO path:
# 1. Start with a specific txid:vout.
# 2. Check whether that exact output has been spent.
# 3. If unspent, report it as the confirmed current endpoint.
# 4. If spent, fetch the spending transaction.
# 5. Select its closest output within the threshold.
# 6. Continue with the new txid:vout and repeat.

# Transaction spent?
# GET /api/tx/{txid}/outspend/{vout}

# {
#   "spent": true,
#   "txid": "spending_transaction_id",
#   "vin": 0
# }

# url = f"https://mempool.space/api/tx/{txid}"