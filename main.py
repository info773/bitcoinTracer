import requests

# https://mempool.space/api/address/1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv/txs

address = "1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv"
url = f"https://mempool.space/api/address/{address}/txs"

# amount= ""

response = requests.get(url)
response.raise_for_status()

data = response.json()

outputs = []

for trans in data:
    for output_index, out in enumerate(trans["vout"]):
        output = {
            "txid": trans["txid"],
            "vout": output_index,
            "amount": out.get("value"),
            "address": out.get("scriptpubkey_address"),
            "time": trans["status"]["block_time"]
        }

        outputs.append(output)

print(outputs)

# Amount/address heuristic:
# 1. Get all transactions for the current address.
# 2. Keep later transactions spending funds from that address.
# 3. Find the outgoing amount closest to the target amount.
# 4. Stop if the difference exceeds the threshold.
# 5. Continue with the receiving address and repeat.
# 6. Report the final address as a possible endpoint.

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