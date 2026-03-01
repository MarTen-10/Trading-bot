import unittest

from core.execution.coinbase_signing import CoinbaseSigner
from core.secrets.provider import SecretsProvider


class FakeSecrets(SecretsProvider):
    def __init__(self, values):
        self.values = values

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)


class CoinbaseSigningTests(unittest.TestCase):
    def test_known_signature_vector(self):
        signer = CoinbaseSigner(FakeSecrets({}))
        secret_b64 = "c2VjcmV0MTIz"
        prehash = "1700000000GET/api/v3/brokerage/accounts"
        expected = "e0XdNk88yto1b5iXtkIDxBN+fkSPMiLO4YfX5Eicoyg="
        self.assertEqual(signer.sign(secret_b64, prehash), expected)

    def test_header_generation(self):
        signer = CoinbaseSigner(
            FakeSecrets(
                {
                    "COINBASE_API_KEY": "key123",
                    "COINBASE_API_SECRET": "c2VjcmV0MTIz",
                    "COINBASE_API_PASSPHRASE": "pass123",
                }
            )
        )
        headers = signer.build_headers(
            method="POST",
            request_path="/api/v3/brokerage/orders",
            body={"b": 2, "a": 1},
            timestamp="1700000000",
        )
        self.assertEqual(headers["CB-ACCESS-KEY"], "key123")
        self.assertEqual(headers["CB-ACCESS-TIMESTAMP"], "1700000000")
        self.assertTrue(headers["CB-ACCESS-SIGN"])
        self.assertEqual(headers["CB-ACCESS-PASSPHRASE"], "pass123")


if __name__ == "__main__":
    unittest.main()
