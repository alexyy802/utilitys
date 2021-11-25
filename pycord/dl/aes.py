from __future__ import unicode_literals

from math import ceil

from .compat import compat_b64decode
from .utils import bytes_to_intlist, intlist_to_bytes

BLOCK_SIZE_BYTES = 16


def aes_ctr_decrypt(data, key, counter):
    """
    Decrypt with aes in counter mode

    @param {int[]} data        cipher
    @param {int[]} key         16/24/32-Byte cipher key
    @param {instance} counter  Instance whose next_value function (@returns {int[]}  16-Byte block)
                               returns the next counter block
    @returns {int[]}           decrypted data
    """
    expanded_key = key_expansion(key)
    block_count = int(ceil(float(len(data)) / BLOCK_SIZE_BYTES))

    decrypted_data = []
    for i in range(block_count):
        counter_block = counter.next_value()
        block = data[i * BLOCK_SIZE_BYTES : (i + 1) * BLOCK_SIZE_BYTES]
        block += [0] * (BLOCK_SIZE_BYTES - len(block))

        cipher_counter_block = aes_encrypt(counter_block, expanded_key)
        decrypted_data += xor(block, cipher_counter_block)
    decrypted_data = decrypted_data[: len(data)]

    return decrypted_data


def aes_cbc_decrypt(data, key, iv):
    """
    Decrypt with aes in CBC mode

    @param {int[]} data        cipher
    @param {int[]} key         16/24/32-Byte cipher key
    @param {int[]} iv          16-Byte IV
    @returns {int[]}           decrypted data
    """
    expanded_key = key_expansion(key)
    block_count = int(ceil(float(len(data)) / BLOCK_SIZE_BYTES))

    decrypted_data = []
    previous_cipher_block = iv
    for i in range(block_count):
        block = data[i * BLOCK_SIZE_BYTES : (i + 1) * BLOCK_SIZE_BYTES]
        block += [0] * (BLOCK_SIZE_BYTES - len(block))

        decrypted_block = aes_decrypt(block, expanded_key)
        decrypted_data += xor(decrypted_block, previous_cipher_block)
        previous_cipher_block = block
    decrypted_data = decrypted_data[: len(data)]

    return decrypted_data


def aes_cbc_encrypt(data, key, iv):
    """
    Encrypt with aes in CBC mode. Using PKCS#7 padding

    @param {int[]} data        cleartext
    @param {int[]} key         16/24/32-Byte cipher key
    @param {int[]} iv          16-Byte IV
    @returns {int[]}           encrypted data
    """
    expanded_key = key_expansion(key)
    block_count = int(ceil(float(len(data)) / BLOCK_SIZE_BYTES))

    encrypted_data = []
    previous_cipher_block = iv
    for i in range(block_count):
        block = data[i * BLOCK_SIZE_BYTES : (i + 1) * BLOCK_SIZE_BYTES]
        remaining_length = BLOCK_SIZE_BYTES - len(block)
        block += [remaining_length] * remaining_length
        mixed_block = xor(block, previous_cipher_block)

        encrypted_block = aes_encrypt(mixed_block, expanded_key)
        encrypted_data += encrypted_block

        previous_cipher_block = encrypted_block

    return encrypted_data


def key_expansion(data):
    """
    Generate key schedule

    @param {int[]} data  16/24/32-Byte cipher key
    @returns {int[]}     176/208/240-Byte expanded key
    """
    data = data[:]  # copy
    rcon_iteration = 1
    key_size_bytes = len(data)
    expanded_key_size_bytes = (key_size_bytes // 4 + 7) * BLOCK_SIZE_BYTES

    while len(data) < expanded_key_size_bytes:
        temp = data[-4:]
        temp = key_schedule_core(temp, rcon_iteration)
        rcon_iteration += 1
        data += xor(temp, data[-key_size_bytes : 4 - key_size_bytes])

        for _ in range(3):
            temp = data[-4:]
            data += xor(temp, data[-key_size_bytes : 4 - key_size_bytes])

        if key_size_bytes == 32:
            temp = data[-4:]
            temp = sub_bytes(temp)
            data += xor(temp, data[-key_size_bytes : 4 - key_size_bytes])

        for _ in range(3 if key_size_bytes == 32 else 2 if key_size_bytes == 24 else 0):
            temp = data[-4:]
            data += xor(temp, data[-key_size_bytes : 4 - key_size_bytes])
    data = data[:expanded_key_size_bytes]

    return data


def aes_encrypt(data, expanded_key):
    """
    Encrypt one block with aes

    @param {int[]} data          16-Byte state
    @param {int[]} expanded_key  176/208/240-Byte expanded key
    @returns {int[]}             16-Byte cipher
    """
    rounds = len(expanded_key) // BLOCK_SIZE_BYTES - 1

    data = xor(data, expanded_key[:BLOCK_SIZE_BYTES])
    for i in range(1, rounds + 1):
        data = sub_bytes(data)
        data = shift_rows(data)
        if i != rounds:
            data = mix_columns(data)
        data = xor(
            data, expanded_key[i * BLOCK_SIZE_BYTES : (i + 1) * BLOCK_SIZE_BYTES]
        )

    return data


def aes_decrypt(data, expanded_key):
    """
    Decrypt one block with aes

    @param {int[]} data          16-Byte cipher
    @param {int[]} expanded_key  176/208/240-Byte expanded key
    @returns {int[]}             16-Byte state
    """
    rounds = len(expanded_key) // BLOCK_SIZE_BYTES - 1

    for i in range(rounds, 0, -1):
        data = xor(
            data, expanded_key[i * BLOCK_SIZE_BYTES : (i + 1) * BLOCK_SIZE_BYTES]
        )
        if i != rounds:
            data = mix_columns_inv(data)
        data = shift_rows_inv(data)
        data = sub_bytes_inv(data)
    data = xor(data, expanded_key[:BLOCK_SIZE_BYTES])

    return data


def aes_decrypt_text(data, password, key_size_bytes):
    """
    Decrypt text
    - The first 8 Bytes of decoded 'data' are the 8 high Bytes of the counter
    - The cipher key is retrieved by encrypting the first 16 Byte of 'password'
      with the first 'key_size_bytes' Bytes from 'password' (if necessary filled with 0's)
    - Mode of operation is 'counter'

    @param {str} data                    Base64 encoded string
    @param {str,unicode} password        Password (will be encoded with utf-8)
    @param {int} key_size_bytes          Possible values: 16 for 128-Bit, 24 for 192-Bit or 32 for 256-Bit
    @returns {str}                       Decrypted data
    """
    NONCE_LENGTH_BYTES = 8

    data = bytes_to_intlist(compat_b64decode(data))
    password = bytes_to_intlist(password.encode("utf-8"))

    key = password[:key_size_bytes] + [0] * (key_size_bytes - len(password))
    key = aes_encrypt(key[:BLOCK_SIZE_BYTES], key_expansion(key)) * (
        key_size_bytes // BLOCK_SIZE_BYTES
    )

    nonce = data[:NONCE_LENGTH_BYTES]
    cipher = data[NONCE_LENGTH_BYTES:]

    class Counter(object):
        __value = nonce + [0] * (BLOCK_SIZE_BYTES - NONCE_LENGTH_BYTES)

        def next_value(self):
            temp = self.__value
            self.__value = inc(self.__value)
            return temp

    decrypted_data = aes_ctr_decrypt(cipher, key, Counter())
    plaintext = intlist_to_bytes(decrypted_data)

    return plaintext


RCON = (0x8D, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)
SBOX = (
    0x63,
    0x7C,
    0x77,
    0x7B,
    0xF2,
    0x6B,
    0x6F,
    0xC5,
    0x30,
    0x01,
    0x67,
    0x2B,
    0xFE,
    0xD7,
    0xAB,
    0x76,
    0xCA,
    0x82,
    0xC9,
    0x7D,
    0xFA,
    0x59,
    0x47,
    0xF0,
    0xAD,
    0xD4,
    0xA2,
    0xAF,
    0x9C,
    0xA4,
    0x72,
    0xC0,
    0xB7,
    0xFD,
    0x93,
    0x26,
    0x36,
    0x3F,
    0xF7,
    0xCC,
    0x34,
    0xA5,
    0xE5,
    0xF1,
    0x71,
    0xD8,
    0x31,
    0x15,
    0x04,
    0xC7,
    0x23,
    0xC3,
    0x18,
    0x96,
    0x05,
    0x9A,
    0x07,
    0x12,
    0x80,
    0xE2,
    0xEB,
    0x27,
    0xB2,
    0x75,
    0x09,
    0x83,
    0x2C,
    0x1A,
    0x1B,
    0x6E,
    0x5A,
    0xA0,
    0x52,
    0x3B,
    0xD6,
    0xB3,
    0x29,
    0xE3,
    0x2F,
    0x84,
    0x53,
    0xD1,
    0x00,
    0xED,
    0x20,
    0xFC,
    0xB1,
    0x5B,
    0x6A,
    0xCB,
    0xBE,
    0x39,
    0x4A,
    0x4C,
    0x58,
    0xCF,
    0xD0,
    0xEF,
    0xAA,
    0xFB,
    0x43,
    0x4D,
    0x33,
    0x85,
    0x45,
    0xF9,
    0x02,
    0x7F,
    0x50,
    0x3C,
    0x9F,
    0xA8,
    0x51,
    0xA3,
    0x40,
    0x8F,
    0x92,
    0x9D,
    0x38,
    0xF5,
    0xBC,
    0xB6,
    0xDA,
    0x21,
    0x10,
    0xFF,
    0xF3,
    0xD2,
    0xCD,
    0x0C,
    0x13,
    0xEC,
    0x5F,
    0x97,
    0x44,
    0x17,
    0xC4,
    0xA7,
    0x7E,
    0x3D,
    0x64,
    0x5D,
    0x19,
    0x73,
    0x60,
    0x81,
    0x4F,
    0xDC,
    0x22,
    0x2A,
    0x90,
    0x88,
    0x46,
    0xEE,
    0xB8,
    0x14,
    0xDE,
    0x5E,
    0x0B,
    0xDB,
    0xE0,
    0x32,
    0x3A,
    0x0A,
    0x49,
    0x06,
    0x24,
    0x5C,
    0xC2,
    0xD3,
    0xAC,
    0x62,
    0x91,
    0x95,
    0xE4,
    0x79,
    0xE7,
    0xC8,
    0x37,
    0x6D,
    0x8D,
    0xD5,
    0x4E,
    0xA9,
    0x6C,
    0x56,
    0xF4,
    0xEA,
    0x65,
    0x7A,
    0xAE,
    0x08,
    0xBA,
    0x78,
    0x25,
    0x2E,
    0x1C,
    0xA6,
    0xB4,
    0xC6,
    0xE8,
    0xDD,
    0x74,
    0x1F,
    0x4B,
    0xBD,
    0x8B,
    0x8A,
    0x70,
    0x3E,
    0xB5,
    0x66,
    0x48,
    0x03,
    0xF6,
    0x0E,
    0x61,
    0x35,
    0x57,
    0xB9,
    0x86,
    0xC1,
    0x1D,
    0x9E,
    0xE1,
    0xF8,
    0x98,
    0x11,
    0x69,
    0xD9,
    0x8E,
    0x94,
    0x9B,
    0x1E,
    0x87,
    0xE9,
    0xCE,
    0x55,
    0x28,
    0xDF,
    0x8C,
    0xA1,
    0x89,
    0x0D,
    0xBF,
    0xE6,
    0x42,
    0x68,
    0x41,
    0x99,
    0x2D,
    0x0F,
    0xB0,
    0x54,
    0xBB,
    0x16,
)
SBOX_INV = (
    0x52,
    0x09,
    0x6A,
    0xD5,
    0x30,
    0x36,
    0xA5,
    0x38,
    0xBF,
    0x40,
    0xA3,
    0x9E,
    0x81,
    0xF3,
    0xD7,
    0xFB,
    0x7C,
    0xE3,
    0x39,
    0x82,
    0x9B,
    0x2F,
    0xFF,
    0x87,
    0x34,
    0x8E,
    0x43,
    0x44,
    0xC4,
    0xDE,
    0xE9,
    0xCB,
    0x54,
    0x7B,
    0x94,
    0x32,
    0xA6,
    0xC2,
    0x23,
    0x3D,
    0xEE,
    0x4C,
    0x95,
    0x0B,
    0x42,
    0xFA,
    0xC3,
    0x4E,
    0x08,
    0x2E,
    0xA1,
    0x66,
    0x28,
    0xD9,
    0x24,
    0xB2,
    0x76,
    0x5B,
    0xA2,
    0x49,
    0x6D,
    0x8B,
    0xD1,
    0x25,
    0x72,
    0xF8,
    0xF6,
    0x64,
    0x86,
    0x68,
    0x98,
    0x16,
    0xD4,
    0xA4,
    0x5C,
    0xCC,
    0x5D,
    0x65,
    0xB6,
    0x92,
    0x6C,
    0x70,
    0x48,
    0x50,
    0xFD,
    0xED,
    0xB9,
    0xDA,
    0x5E,
    0x15,
    0x46,
    0x57,
    0xA7,
    0x8D,
    0x9D,
    0x84,
    0x90,
    0xD8,
    0xAB,
    0x00,
    0x8C,
    0xBC,
    0xD3,
    0x0A,
    0xF7,
    0xE4,
    0x58,
    0x05,
    0xB8,
    0xB3,
    0x45,
    0x06,
    0xD0,
    0x2C,
    0x1E,
    0x8F,
    0xCA,
    0x3F,
    0x0F,
    0x02,
    0xC1,
    0xAF,
    0xBD,
    0x03,
    0x01,
    0x13,
    0x8A,
    0x6B,
    0x3A,
    0x91,
    0x11,
    0x41,
    0x4F,
    0x67,
    0xDC,
    0xEA,
    0x97,
    0xF2,
    0xCF,
    0xCE,
    0xF0,
    0xB4,
    0xE6,
    0x73,
    0x96,
    0xAC,
    0x74,
    0x22,
    0xE7,
    0xAD,
    0x35,
    0x85,
    0xE2,
    0xF9,
    0x37,
    0xE8,
    0x1C,
    0x75,
    0xDF,
    0x6E,
    0x47,
    0xF1,
    0x1A,
    0x71,
    0x1D,
    0x29,
    0xC5,
    0x89,
    0x6F,
    0xB7,
    0x62,
    0x0E,
    0xAA,
    0x18,
    0xBE,
    0x1B,
    0xFC,
    0x56,
    0x3E,
    0x4B,
    0xC6,
    0xD2,
    0x79,
    0x20,
    0x9A,
    0xDB,
    0xC0,
    0xFE,
    0x78,
    0xCD,
    0x5A,
    0xF4,
    0x1F,
    0xDD,
    0xA8,
    0x33,
    0x88,
    0x07,
    0xC7,
    0x31,
    0xB1,
    0x12,
    0x10,
    0x59,
    0x27,
    0x80,
    0xEC,
    0x5F,
    0x60,
    0x51,
    0x7F,
    0xA9,
    0x19,
    0xB5,
    0x4A,
    0x0D,
    0x2D,
    0xE5,
    0x7A,
    0x9F,
    0x93,
    0xC9,
    0x9C,
    0xEF,
    0xA0,
    0xE0,
    0x3B,
    0x4D,
    0xAE,
    0x2A,
    0xF5,
    0xB0,
    0xC8,
    0xEB,
    0xBB,
    0x3C,
    0x83,
    0x53,
    0x99,
    0x61,
    0x17,
    0x2B,
    0x04,
    0x7E,
    0xBA,
    0x77,
    0xD6,
    0x26,
    0xE1,
    0x69,
    0x14,
    0x63,
    0x55,
    0x21,
    0x0C,
    0x7D,
)
MIX_COLUMN_MATRIX = (
    (0x2, 0x3, 0x1, 0x1),
    (0x1, 0x2, 0x3, 0x1),
    (0x1, 0x1, 0x2, 0x3),
    (0x3, 0x1, 0x1, 0x2),
)
MIX_COLUMN_MATRIX_INV = (
    (0xE, 0xB, 0xD, 0x9),
    (0x9, 0xE, 0xB, 0xD),
    (0xD, 0x9, 0xE, 0xB),
    (0xB, 0xD, 0x9, 0xE),
)
RIJNDAEL_EXP_TABLE = (
    0x01,
    0x03,
    0x05,
    0x0F,
    0x11,
    0x33,
    0x55,
    0xFF,
    0x1A,
    0x2E,
    0x72,
    0x96,
    0xA1,
    0xF8,
    0x13,
    0x35,
    0x5F,
    0xE1,
    0x38,
    0x48,
    0xD8,
    0x73,
    0x95,
    0xA4,
    0xF7,
    0x02,
    0x06,
    0x0A,
    0x1E,
    0x22,
    0x66,
    0xAA,
    0xE5,
    0x34,
    0x5C,
    0xE4,
    0x37,
    0x59,
    0xEB,
    0x26,
    0x6A,
    0xBE,
    0xD9,
    0x70,
    0x90,
    0xAB,
    0xE6,
    0x31,
    0x53,
    0xF5,
    0x04,
    0x0C,
    0x14,
    0x3C,
    0x44,
    0xCC,
    0x4F,
    0xD1,
    0x68,
    0xB8,
    0xD3,
    0x6E,
    0xB2,
    0xCD,
    0x4C,
    0xD4,
    0x67,
    0xA9,
    0xE0,
    0x3B,
    0x4D,
    0xD7,
    0x62,
    0xA6,
    0xF1,
    0x08,
    0x18,
    0x28,
    0x78,
    0x88,
    0x83,
    0x9E,
    0xB9,
    0xD0,
    0x6B,
    0xBD,
    0xDC,
    0x7F,
    0x81,
    0x98,
    0xB3,
    0xCE,
    0x49,
    0xDB,
    0x76,
    0x9A,
    0xB5,
    0xC4,
    0x57,
    0xF9,
    0x10,
    0x30,
    0x50,
    0xF0,
    0x0B,
    0x1D,
    0x27,
    0x69,
    0xBB,
    0xD6,
    0x61,
    0xA3,
    0xFE,
    0x19,
    0x2B,
    0x7D,
    0x87,
    0x92,
    0xAD,
    0xEC,
    0x2F,
    0x71,
    0x93,
    0xAE,
    0xE9,
    0x20,
    0x60,
    0xA0,
    0xFB,
    0x16,
    0x3A,
    0x4E,
    0xD2,
    0x6D,
    0xB7,
    0xC2,
    0x5D,
    0xE7,
    0x32,
    0x56,
    0xFA,
    0x15,
    0x3F,
    0x41,
    0xC3,
    0x5E,
    0xE2,
    0x3D,
    0x47,
    0xC9,
    0x40,
    0xC0,
    0x5B,
    0xED,
    0x2C,
    0x74,
    0x9C,
    0xBF,
    0xDA,
    0x75,
    0x9F,
    0xBA,
    0xD5,
    0x64,
    0xAC,
    0xEF,
    0x2A,
    0x7E,
    0x82,
    0x9D,
    0xBC,
    0xDF,
    0x7A,
    0x8E,
    0x89,
    0x80,
    0x9B,
    0xB6,
    0xC1,
    0x58,
    0xE8,
    0x23,
    0x65,
    0xAF,
    0xEA,
    0x25,
    0x6F,
    0xB1,
    0xC8,
    0x43,
    0xC5,
    0x54,
    0xFC,
    0x1F,
    0x21,
    0x63,
    0xA5,
    0xF4,
    0x07,
    0x09,
    0x1B,
    0x2D,
    0x77,
    0x99,
    0xB0,
    0xCB,
    0x46,
    0xCA,
    0x45,
    0xCF,
    0x4A,
    0xDE,
    0x79,
    0x8B,
    0x86,
    0x91,
    0xA8,
    0xE3,
    0x3E,
    0x42,
    0xC6,
    0x51,
    0xF3,
    0x0E,
    0x12,
    0x36,
    0x5A,
    0xEE,
    0x29,
    0x7B,
    0x8D,
    0x8C,
    0x8F,
    0x8A,
    0x85,
    0x94,
    0xA7,
    0xF2,
    0x0D,
    0x17,
    0x39,
    0x4B,
    0xDD,
    0x7C,
    0x84,
    0x97,
    0xA2,
    0xFD,
    0x1C,
    0x24,
    0x6C,
    0xB4,
    0xC7,
    0x52,
    0xF6,
    0x01,
)
RIJNDAEL_LOG_TABLE = (
    0x00,
    0x00,
    0x19,
    0x01,
    0x32,
    0x02,
    0x1A,
    0xC6,
    0x4B,
    0xC7,
    0x1B,
    0x68,
    0x33,
    0xEE,
    0xDF,
    0x03,
    0x64,
    0x04,
    0xE0,
    0x0E,
    0x34,
    0x8D,
    0x81,
    0xEF,
    0x4C,
    0x71,
    0x08,
    0xC8,
    0xF8,
    0x69,
    0x1C,
    0xC1,
    0x7D,
    0xC2,
    0x1D,
    0xB5,
    0xF9,
    0xB9,
    0x27,
    0x6A,
    0x4D,
    0xE4,
    0xA6,
    0x72,
    0x9A,
    0xC9,
    0x09,
    0x78,
    0x65,
    0x2F,
    0x8A,
    0x05,
    0x21,
    0x0F,
    0xE1,
    0x24,
    0x12,
    0xF0,
    0x82,
    0x45,
    0x35,
    0x93,
    0xDA,
    0x8E,
    0x96,
    0x8F,
    0xDB,
    0xBD,
    0x36,
    0xD0,
    0xCE,
    0x94,
    0x13,
    0x5C,
    0xD2,
    0xF1,
    0x40,
    0x46,
    0x83,
    0x38,
    0x66,
    0xDD,
    0xFD,
    0x30,
    0xBF,
    0x06,
    0x8B,
    0x62,
    0xB3,
    0x25,
    0xE2,
    0x98,
    0x22,
    0x88,
    0x91,
    0x10,
    0x7E,
    0x6E,
    0x48,
    0xC3,
    0xA3,
    0xB6,
    0x1E,
    0x42,
    0x3A,
    0x6B,
    0x28,
    0x54,
    0xFA,
    0x85,
    0x3D,
    0xBA,
    0x2B,
    0x79,
    0x0A,
    0x15,
    0x9B,
    0x9F,
    0x5E,
    0xCA,
    0x4E,
    0xD4,
    0xAC,
    0xE5,
    0xF3,
    0x73,
    0xA7,
    0x57,
    0xAF,
    0x58,
    0xA8,
    0x50,
    0xF4,
    0xEA,
    0xD6,
    0x74,
    0x4F,
    0xAE,
    0xE9,
    0xD5,
    0xE7,
    0xE6,
    0xAD,
    0xE8,
    0x2C,
    0xD7,
    0x75,
    0x7A,
    0xEB,
    0x16,
    0x0B,
    0xF5,
    0x59,
    0xCB,
    0x5F,
    0xB0,
    0x9C,
    0xA9,
    0x51,
    0xA0,
    0x7F,
    0x0C,
    0xF6,
    0x6F,
    0x17,
    0xC4,
    0x49,
    0xEC,
    0xD8,
    0x43,
    0x1F,
    0x2D,
    0xA4,
    0x76,
    0x7B,
    0xB7,
    0xCC,
    0xBB,
    0x3E,
    0x5A,
    0xFB,
    0x60,
    0xB1,
    0x86,
    0x3B,
    0x52,
    0xA1,
    0x6C,
    0xAA,
    0x55,
    0x29,
    0x9D,
    0x97,
    0xB2,
    0x87,
    0x90,
    0x61,
    0xBE,
    0xDC,
    0xFC,
    0xBC,
    0x95,
    0xCF,
    0xCD,
    0x37,
    0x3F,
    0x5B,
    0xD1,
    0x53,
    0x39,
    0x84,
    0x3C,
    0x41,
    0xA2,
    0x6D,
    0x47,
    0x14,
    0x2A,
    0x9E,
    0x5D,
    0x56,
    0xF2,
    0xD3,
    0xAB,
    0x44,
    0x11,
    0x92,
    0xD9,
    0x23,
    0x20,
    0x2E,
    0x89,
    0xB4,
    0x7C,
    0xB8,
    0x26,
    0x77,
    0x99,
    0xE3,
    0xA5,
    0x67,
    0x4A,
    0xED,
    0xDE,
    0xC5,
    0x31,
    0xFE,
    0x18,
    0x0D,
    0x63,
    0x8C,
    0x80,
    0xC0,
    0xF7,
    0x70,
    0x07,
)


def sub_bytes(data):
    return [SBOX[x] for x in data]


def sub_bytes_inv(data):
    return [SBOX_INV[x] for x in data]


def rotate(data):
    return data[1:] + [data[0]]


def key_schedule_core(data, rcon_iteration):
    data = rotate(data)
    data = sub_bytes(data)
    data[0] = data[0] ^ RCON[rcon_iteration]

    return data


def xor(data1, data2):
    return [x ^ y for x, y in zip(data1, data2)]


def rijndael_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return RIJNDAEL_EXP_TABLE[(RIJNDAEL_LOG_TABLE[a] + RIJNDAEL_LOG_TABLE[b]) % 0xFF]


def mix_column(data, matrix):
    data_mixed = []
    for row in range(4):
        mixed = 0
        for column in range(4):
            # xor is (+) and (-)
            mixed ^= rijndael_mul(data[column], matrix[row][column])
        data_mixed.append(mixed)
    return data_mixed


def mix_columns(data, matrix=MIX_COLUMN_MATRIX):
    data_mixed = []
    for i in range(4):
        column = data[i * 4 : (i + 1) * 4]
        data_mixed += mix_column(column, matrix)
    return data_mixed


def mix_columns_inv(data):
    return mix_columns(data, MIX_COLUMN_MATRIX_INV)


def shift_rows(data):
    data_shifted = []
    for column in range(4):
        for row in range(4):
            data_shifted.append(data[((column + row) & 0b11) * 4 + row])
    return data_shifted


def shift_rows_inv(data):
    data_shifted = []
    for column in range(4):
        for row in range(4):
            data_shifted.append(data[((column - row) & 0b11) * 4 + row])
    return data_shifted


def inc(data):
    data = data[:]  # copy
    for i in range(len(data) - 1, -1, -1):
        if data[i] == 255:
            data[i] = 0
        else:
            data[i] = data[i] + 1
            break
    return data


__all__ = [
    "aes_encrypt",
    "key_expansion",
    "aes_ctr_decrypt",
    "aes_cbc_decrypt",
    "aes_decrypt_text",
]
