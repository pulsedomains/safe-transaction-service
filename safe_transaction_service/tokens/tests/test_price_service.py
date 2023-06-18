from unittest import mock
from unittest.mock import MagicMock

from django.test import TestCase

from eth_account import Account

from gnosis.eth import EthereumClient, EthereumClientProvider, EthereumNetwork
from gnosis.eth.oracles import KyberOracle, OracleException, UnderlyingToken

from safe_transaction_service.history.tests.utils import just_test_if_mainnet_node
from safe_transaction_service.utils.redis import get_redis

from ..clients import CannotGetPrice, CoingeckoClient, KrakenClient, KucoinClient
from ..services.price_service import PriceService, PriceServiceProvider


class TestPriceService(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.redis = get_redis()
        cls.ethereum_client = EthereumClientProvider()

    @classmethod
    def tearDownClass(cls) -> None:
        PriceServiceProvider.del_singleton()

    def setUp(self) -> None:
        self.price_service = PriceServiceProvider()

    def tearDown(self) -> None:
        PriceServiceProvider.del_singleton()

    def test_available_price_oracles(self):
        # Ganache should have no oracle enabled
        self.assertEqual(len(self.price_service.enabled_price_oracles), 0)
        self.assertEqual(len(self.price_service.enabled_price_pool_oracles), 0)
        self.assertEqual(len(self.price_service.enabled_composed_price_oracles), 0)

    def test_available_price_oracles_mainnet(self):
        # Mainnet should have every oracle enabled
        mainnet_node = just_test_if_mainnet_node()
        price_service = PriceService(EthereumClient(mainnet_node), self.redis)
        self.assertEqual(len(price_service.enabled_price_oracles), 6)
        self.assertEqual(len(price_service.enabled_price_pool_oracles), 3)
        self.assertEqual(len(price_service.enabled_composed_price_oracles), 4)

    @mock.patch.object(KrakenClient, "get_ether_usd_price", return_value=0.4)
    @mock.patch.object(KucoinClient, "get_ether_usd_price", return_value=0.5)
    def test_get_ether_usd_price(self, kucoin_mock: MagicMock, kraken_mock: MagicMock):
        price_service = self.price_service
        eth_usd_price = price_service.get_ether_usd_price()
        self.assertEqual(eth_usd_price, kraken_mock.return_value)
        kucoin_mock.assert_not_called()

        kraken_mock.side_effect = CannotGetPrice

        # cache_ether_usd_price is working
        eth_usd_price = price_service.get_native_coin_usd_price()
        self.assertEqual(eth_usd_price, kraken_mock.return_value)

        # Clear cache_ether_usd_price
        price_service.cache_ether_usd_price.clear()
        self.assertEqual(eth_usd_price, kraken_mock.return_value)
        kucoin_mock.assert_not_called()

    def test_get_native_coin_usd_price(self):
        price_service = self.price_service

        # Unsupported network (Ganache)
        with mock.patch.object(
            KrakenClient, "get_ether_usd_price", return_value=1_600
        ) as kraken_mock:
            price_service.cache_native_coin_usd_price.clear()
            self.assertEqual(price_service.get_native_coin_usd_price(), 1_600)

            # Test cache is working
            kraken_mock.side_effect = CannotGetPrice
            self.assertEqual(price_service.get_native_coin_usd_price(), 1_600)

    def test_get_token_eth_value(self):
        mainnet_node = just_test_if_mainnet_node()
        price_service = PriceService(EthereumClient(mainnet_node), self.redis)
        gno_token_address = "0x6810e776880C02933D47DB1b9fc05908e5386b96"
        token_eth_value = price_service.get_token_eth_value(gno_token_address)
        self.assertIsInstance(token_eth_value, float)
        self.assertGreater(token_eth_value, 0)

    @mock.patch.object(KyberOracle, "get_price", return_value=1.23, autospec=True)
    def test_get_token_eth_value_mocked(self, kyber_get_price_mock: MagicMock):
        price_service = self.price_service
        oracle_1 = mock.MagicMock()
        oracle_1.get_price.return_value = 1.23
        oracle_2 = mock.MagicMock()
        oracle_3 = mock.MagicMock()
        price_service.enabled_price_oracles = (oracle_1, oracle_2, oracle_3)
        self.assertEqual(len(price_service.enabled_price_oracles), 3)
        random_address = Account.create().address
        self.assertEqual(len(price_service.cache_token_eth_value), 0)

        self.assertEqual(price_service.get_token_eth_value(random_address), 1.23)
        self.assertEqual(price_service.cache_token_eth_value[(random_address,)], 1.23)

        # Make every oracle fail
        oracle_1.get_price.side_effect = OracleException
        oracle_2.get_price.side_effect = OracleException
        oracle_3.get_price.side_effect = OracleException

        # Check cache
        self.assertEqual(price_service.get_token_eth_value(random_address), 1.23)
        random_address_2 = Account.create().address
        self.assertEqual(price_service.get_token_eth_value(random_address_2), 0.0)
        self.assertEqual(price_service.cache_token_eth_value[(random_address,)], 1.23)
        self.assertEqual(price_service.cache_token_eth_value[(random_address_2,)], 0.0)

    @mock.patch.object(
        PriceService, "get_underlying_tokens", return_value=[], autospec=True
    )
    @mock.patch.object(
        PriceService, "get_token_eth_value", autospec=True, return_value=1.0
    )
    def test_get_token_eth_price_from_composed_oracles(
        self, get_token_eth_value_mock: MagicMock, price_service_mock: MagicMock
    ):
        price_service = self.price_service
        token_one = UnderlyingToken("0x48f07301E9E29c3C38a80ae8d9ae771F224f1054", 0.482)
        token_two = UnderlyingToken("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 0.376)
        token_three = UnderlyingToken("0xA0b86991c6218b36c1d19D4a2e9Eb0cE360", 0.142)
        price_service_mock.return_value = [token_one, token_two, token_three]
        curve_price = "0xe7ce624c00381b4b7abb03e633fb4acac4537dd6"
        eth_price = price_service.get_token_eth_price_from_composed_oracles(curve_price)
        self.assertEqual(eth_price, 1.0)
