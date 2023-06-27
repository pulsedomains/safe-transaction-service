import logging

from .base_client import BaseHTTPClient
from .exceptions import CannotGetPrice

logger = logging.getLogger(__name__)


class KucoinClient(BaseHTTPClient):
    def _get_price(self, symbol: str):
        url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol}"

        try:
            response = self.http_session.get(url, timeout=self.request_timeout)
            result = response.json()
            return float(result["data"]["price"])
        except (ValueError, IOError) as e:
            logger.warning("Cannot get price from url=%s", url)
            raise CannotGetPrice from e

    def get_ether_usd_price(self) -> float:
        """
        :return: current USD price for ETH Coin
        :raises: CannotGetPrice
        """
        return self._get_price("ETH-USDT")

