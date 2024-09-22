import binascii

def to_hex(data: bytes) -> str:
    return binascii.hexlify(data).decode('utf-8')

def from_hex(hex_string: str) -> bytes:
    return binascii.unhexlify(hex_string)
