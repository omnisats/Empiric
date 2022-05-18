import asyncio
import os

from pontis.admin.client import PontisAdminClient
from starkware.crypto.signature.signature import private_to_stark_key

publishers = [
    "pontis-coinapi",
    "pontis-coinmarketcap",
    "pontis-coingecko",
    "pontis-coinbase",
    "pontis-gemini",
    "pontis-binance",
    "pontis-ftx",
]
public_keys = [
    private_to_stark_key(int(os.environ.get("COINAPI_PUBLISHER_PRIVATE_KEY"))),
    private_to_stark_key(int(os.environ.get("COINMARKETCAP_PUBLISHER_PRIVATE_KEY"))),
    private_to_stark_key(int(os.environ.get("COINGECKO_PUBLISHER_PRIVATE_KEY"))),
    private_to_stark_key(int(os.environ.get("COINBASE_PUBLISHER_PRIVATE_KEY"))),
    private_to_stark_key(int(os.environ.get("GEMINI_PUBLISHER_PRIVATE_KEY"))),
    private_to_stark_key(int(os.environ.get("BINANCE_PUBLISHER_PRIVATE_KEY"))),
    private_to_stark_key(int(os.environ.get("FTX_PUBLISHER_PRIVATE_KEY"))),
]


async def main():
    admin_private_key = int(os.environ.get("ADMIN_PRIVATE_KEY"))
    admin_client = PontisAdminClient(
        admin_private_key,
    )
    for public_key, publisher in zip(public_keys, publishers):
        await admin_client.register_publisher_if_not_registered(public_key, publisher)


if __name__ == "__main__":

    asyncio.run(main())