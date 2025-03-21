from django.test import TestCase

from gnosis.eth import EthereumNetwork

from safe_transaction_service.history.tests.utils import skip_on

from ...clients import CannotGetPrice
from ...clients.coingecko_client import CoingeckoClient
from ...clients.exceptions import CoingeckoRateLimitError


class TestCoingeckoClient(TestCase):
    GNO_TOKEN_ADDRESS = "0x6810e776880C02933D47DB1b9fc05908e5386b96"
    GNO_GNOSIS_CHAIN_ADDRESS = "0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb"

    @skip_on(CannotGetPrice, reason="Cannot get price from Coingecko")
    def test_coingecko_client(self):
        self.assertTrue(CoingeckoClient.supports_network(EthereumNetwork.MAINNET))
        self.assertTrue(CoingeckoClient.supports_network(EthereumNetwork.PULSECHAIN_MAINNET))

        # Test Mainnet
        coingecko_client = CoingeckoClient()
        non_existing_token_address = "0xda2f8b8386302C354a90DB670E40beA3563AF454"
        self.assertGreater(coingecko_client.get_token_price(self.GNO_TOKEN_ADDRESS), 0)
        with self.assertRaises(CannotGetPrice):
            coingecko_client.get_token_price(non_existing_token_address)

    @skip_on(CoingeckoRateLimitError, reason="Coingecko rate limit reached")
    def test_get_logo_url(self):
        # Test Mainnet
        coingecko_client = CoingeckoClient()
        self.assertIn(
            "http", coingecko_client.get_token_logo_url(self.GNO_TOKEN_ADDRESS)
        )
        self.assertIsNone(
            coingecko_client.get_token_logo_url(self.GNO_GNOSIS_CHAIN_ADDRESS)
        )

