import logging
import time
from typing import List

from aiohttp import ClientSession
from empiric.core.entry import Entry
from empiric.core.utils import currency_pair_to_key
from empiric.publisher.assets import EmpiricAsset
from empiric.publisher.base import PublisherInterfaceT

logger = logging.getLogger(__name__)


class GeminiFetcher(PublisherInterfaceT):
    BASE_URL: str = "https://api.gemini.com/v1"
    SOURCE: str = "gemini"

    publisher: str

    def __init__(self, assets: List[EmpiricAsset], publisher):
        self.assets = assets
        self.publisher = publisher

    async def fetch(self, session: ClientSession) -> List[Entry]:
        entries = []
        async with session.get(self.BASE_URL + "/pricefeed") as resp:
            result_json = await resp.json()
            for asset in self.assets:
                if asset["type"] != "SPOT":
                    logger.debug(f"Skipping Gemini for non-spot asset {asset}")
                    continue

                pair = asset["pair"]
                key = currency_pair_to_key(*pair)
                timestamp = int(time.time())
                result = [e for e in result_json if e["pair"] == "".join(pair)]

                if len(result) == 0:
                    logger.debug(f"No entry found for {key} from Gemini")
                    continue

                if len(result) > 1:
                    raise ValueError(
                        f"Found more than one matching entries for Gemini response and price pair {pair}"
                    )

                price = float(result[0]["price"])
                price_int = int(price * (10 ** asset["decimals"]))

                logger.info(f"Fetched price {price} for {key} from Gemini")

                entries.append(
                    Entry(
                        key=key,
                        value=price_int,
                        timestamp=timestamp,
                        source=self.SOURCE,
                        publisher=self.publisher,
                    )
                )
            return entries
