import unittest

from .key_ops import KeyDescriptor, IncorrectPassword


class KeyDescriptorTest(unittest.TestCase):
    def test_generate_and_valid_open(self):
        key_desc, key = KeyDescriptor.generate("password123", 'argon2id_weak')
        key_copy = key_desc.open("password123")
        self.assertEqual(key, key_copy)

    def test_generate_and_invalid_open(self):
        key_desc, key = KeyDescriptor.generate("password123", 'argon2id_weak')
        with self.assertRaises(IncorrectPassword):
            key_desc.open("password1234")


if __name__ == '__main__':
    unittest.main()
