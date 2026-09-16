import requests

# https://mempool.space/api/address/1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv/txs

address = "1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv"
url = f"https://mempool.space/api/address/{address}/txs"

amount= ""

response = requests.get(url)
response.raise_for_status()

data = response.json()

outputs = []

for trans in data:
    for out in trans["vout"]:
        output = {
            "amount": out["value"],
            "address": out.get("scriptpubkey_address"),
            "time": trans["status"]["block_time"]
        }

        outputs.append(output)

print(outputs)