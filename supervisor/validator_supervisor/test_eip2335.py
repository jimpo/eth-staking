import json
import unittest

from .eip2335 import EIP2335KeystoreSchema


TEST_VALIDATOR = "0xb20e453a8e770ec50ca4129e0fc12b2ac1f3a720f519a124369b0c838c27da04910a8294fb96a6b8d3c7036a74740a32"
with open(f"test_canonical/validators/{TEST_VALIDATOR}/keystore.json") as f:
    TEST_KEYSTORE = f.read()


class EIP2335Test(unittest.TestCase):
    def test_serialize_deserialize_keystore(self):
        keystore_data = json.loads(TEST_KEYSTORE)
        keystore = EIP2335KeystoreSchema().load(keystore_data)
        self.assertEqual(keystore.pubkey, TEST_VALIDATOR[2:])


if __name__ == '__main__':
    unittest.main()
