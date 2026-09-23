from datetime import datetime, timezone

import requests
from rich.pretty import pprint

# https://mempool.space/api/address/1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv/txs

address = "1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv"

# TIME year, month, day, hour, minute, timezone
dt_original = datetime(2014, 5, 1, 0, 0, tzinfo=timezone.utc)

# AMOUNT in satoshis + THRESHOLD in percent

amount_original = 13_370_000
threshold = 15








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
    
    url = f"https://mempool.space/api/address/{address}/txs"

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    outputs = []



    # generate list with needed information per tx
    for trans in data:

        # Check whether the current address is actually an input
        address_is_input = any(
            vin.get("prevout", {}).get("scriptpubkey_address") == address
            for vin in trans["vin"]
        )

        # Ignore transactions where the current address did not spend funds
        if not address_is_input:
            continue

        for output_index, out in enumerate(trans["vout"]):

            # Ignore outputs going back to the current address
            if out.get("scriptpubkey_address") == address:
                continue

            output = {
                "txid": trans["txid"],
                "vout": output_index,
                "amount": out.get("value"),
                "address": out.get("scriptpubkey_address"),
                "time": trans["status"].get("block_time")
            }

            outputs.append(output)

    # filter all tx before the original tx
    filtered_date_outputs = [tx for tx in outputs
                        if tx["time"] is not None
                        and tx["time"] > dt_original_unix
                        ]

    if not filtered_date_outputs:
        print("STOP:No outputs after the original date.")
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

pprint(last_output)





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