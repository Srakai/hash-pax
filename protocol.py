import struct
from enum import Enum
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import binascii
from uuid import UUID
import base64

# Message type enumeration
class PaxMessageType(Enum):
    ActualTemp = 1
    HeaterSetPoint = 2
    Battery = 3
    Usage = 4
    UsageLimit = 5
    LockStatus = 6
    ChargeStatus = 7
    PodInserted = 8
    Time = 9
    DisplayName = 10
    HeaterRanges = 17
    DynamicMode = 19
    ColorTheme = 20
    Brightness = 21
    HapticMode = 23
    SupportedAttributes = 24
    HeatingParams = 25
    UiMode = 27
    ShellColor = 28
    LowSoCMode = 30
    CurrentTargetTemp = 31
    HeatingState = 32
    Haptics = 40
    StatusUpdate = 254


class DynamicMode(Enum):
    Standard = 0
    Boost = 1
    Efficiency = 2
    Stealth = 3
    Flavor = 4


DEVICE_KEY_KEY = '98hmw494dTCGKTvVfdMlQA=='
IV_LENGTH = 16

DEVICE_INFO_SERVICE = UUID("0000180A-0000-1000-8000-00805F9B34FB")
MODEL_NUMBER_CHARACTERISTIC = UUID("00002A24-0000-1000-8000-00805F9B34FB")
SERIAL_NUMBER_CHARACTERISTIC = UUID("00002A25-0000-1000-8000-00805F9B34FB")
SW_REV_CHARACTERISTIC = UUID("00002A26-0000-1000-8000-00805F9B34FB")
HW_REV_CHARACTERISTIC = UUID("00002A27-0000-1000-8000-00805F9B34FB")
MANUFACTURER_CHARACTERISTIC = UUID("00002A29-0000-1000-8000-00805F9B34FB")

PAX_SERVICE = UUID("8E320200-64D2-11E6-BDF4-0800200C9A66")
PAX_READ_CHARACTERISTIC = UUID("8E320201-64D2-11E6-BDF4-0800200C9A66")
PAX_WRITE_CHARACTERISTIC = UUID("8E320202-64D2-11E6-BDF4-0800200C9A66")
PAX_NOTIFY_CHARACTERISTIC = UUID("8E320203-64D2-11E6-BDF4-0800200C9A66")

def derive_shared_key(serial: str) -> bytes:
    """
    Derive the shared device key using the serial number, AES encryption with ECB mode.
    The serial is repeated twice to form a 16-byte string.
    """
    serial_str = (serial * 2).encode('utf-8')
    cipher = AES.new(base64.b64decode(DEVICE_KEY_KEY), AES.MODE_ECB)
    return cipher.encrypt(serial_str)

def decrypt_packet(packet: bytes, device_key) -> bytes:
    """
    Decrypts a packet using AES-OFB mode. The last 16 bytes are the IV.
    """
    if len(packet) <= IV_LENGTH:
        raise ValueError("Invalid packet length")

    data = packet[:-IV_LENGTH]
    iv = packet[-IV_LENGTH:]

    cipher = AES.new(device_key, AES.MODE_OFB, iv=iv)
    decrypted = cipher.decrypt(data)
    return decrypted

def encrypt_packet(plaintext: bytes, device_key) -> bytes:
    """
    Encrypts a packet using AES-OFB mode with a random IV and pads to 64 bytes.
    """
    iv = get_random_bytes(IV_LENGTH)
    
    # Pad the plaintext to 64 bytes
    if len(plaintext) < 16:
        plaintext = plaintext.ljust(16, b'\x00')
    
    cipher = AES.new(device_key, AES.MODE_OFB, iv=iv)
    encrypted = cipher.encrypt(plaintext)
    return encrypted + iv


def encode_temperature_message(temperature: float) -> bytes:
    """
    Encodes a temperature message for the Pax device, pads it 
    to 64 bytes.
    """
    temp_encoded = int(temperature * 10)
    message = struct.pack('<BH', PaxMessageType.HeaterSetPoint.value, temp_encoded)
    msg = pad_to_16_bytes(message)
    print(f"Encoded message: {to_hex(msg)}")
    return msg


def encode_lock_message(lock: bool) -> bytes:
    """
    Encodes a lock/unlock message for the Pax device.
    """
    return struct.pack('BB', PaxMessageType.LockStatus.value, 1 if lock else 0)

def encode_status_update_message(attributes: set) -> bytes:
    """
    Encodes a status update message with a bitmask for requested attributes, pads it to 64 bytes.
    """
    bitmask = 0
    for attr in attributes:
        if attr.value <= 63:
            bitmask |= (1 << attr.value)
    message = struct.pack('<BQ', PaxMessageType.StatusUpdate.value, bitmask)
    msg = pad_to_16_bytes(message)
    print(f"Encoded message: {to_hex(msg)}")
    return msg


def decode_dynamic_mode(data):
    if len(data) < 2:
        raise ValueError("Data too small for DynamicModeMessage")
    mode = data[1]
    return DynamicMode(mode)

def encode_dynamic_mode(mode: DynamicMode) -> bytes:
    """
    Encodes a dynamic mode message, pads it to 64 bytes.
    """
    message = struct.pack('BB', PaxMessageType.DynamicMode.value, mode.value)
    return pad_to_16_bytes(message)

# Mode Enum for Dynamic Mode
def handle_incoming_message(data: bytes) -> str:
    """
    Handles and interprets incoming messages based on the Pax protocol.
    """
    try:
        message_type = PaxMessageType(data[0])
    except ValueError:
        return f"Unknown message type: {data[0]:02x}"

    if message_type == PaxMessageType.Battery:
        battery_level = data[1]
        return f"Battery Level: {battery_level}%"
    
    elif message_type == PaxMessageType.ChargeStatus:
        charging = data[1] != 0
        return f"Charging: {'Yes' if charging else 'No'}"
    
    elif message_type == PaxMessageType.LockStatus:
        lock_state = data[1] != 0
        return f"Device is {'Locked' if lock_state else 'Unlocked'}"
    
    elif message_type == PaxMessageType.HeaterSetPoint:
        temperature = struct.unpack('<H', data[1:3])[0] / 10.0
        return f"Temperature Set Point: {temperature}°C"
    
    elif message_type == PaxMessageType.ActualTemp:
        temperature = struct.unpack('<H', data[1:3])[0] / 10.0
        return f"Actual Temperature: {temperature}°C"
    
    elif message_type == PaxMessageType.CurrentTargetTemp:
        temperature = struct.unpack('<H', data[1:3])[0] / 10.0
        return f"Current Target Temperature: {temperature}°C"
    
    elif message_type == PaxMessageType.SupportedAttributes:
        bitmask = struct.unpack('<Q', data[1:9])[0]
        supported_attrs = {PaxMessageType(attr) for attr in range(64) if bitmask & (1 << attr)}
        return f"Supported Attributes: {', '.join([attr.name for attr in supported_attrs])}"
    
    elif message_type == PaxMessageType.StatusUpdate:
        bitmask = struct.unpack('<Q', data[1:9])[0]
        updated_attrs = {PaxMessageType(attr) for attr in range(64) if bitmask & (1 << attr)}
        return f"Updated Attributes: {', '.join([attr.name for attr in updated_attrs])}"
    
    elif message_type == PaxMessageType.DynamicMode:
        mode = data[1]
        return f"Dynamic Mode: {mode}"
    
    elif message_type == PaxMessageType.ColorTheme:
        theme = data[1]
        return f"Color Theme: {theme}"
    
    elif message_type == PaxMessageType.Brightness:
        brightness = data[1]
        return f"Brightness: {brightness}"
    
    elif message_type == PaxMessageType.HapticMode:
        haptic_mode = data[1]
        return f"Haptic Mode: {haptic_mode}"
    
    elif message_type == PaxMessageType.UiMode:
        ui_mode = data[1]
        return f"UI Mode: {ui_mode}"
    
    elif message_type == PaxMessageType.LowSoCMode:
        low_soc_mode = data[1]
        return f"Low SoC Mode: {low_soc_mode}"
    
    elif message_type == PaxMessageType.HeatingState:
        heating_state = data[1]
        return f"Heating State: {heating_state}"

    return f"Unknown message type: {message_type}"


# Helper functions
def to_hex(data: bytes) -> str:
    return binascii.hexlify(data).decode('utf-8')

def pad_to_16_bytes(data: bytes) -> bytes:
    """
    Pads the given data to 64 bytes using null bytes.
    """
    return data.ljust(16, b'\x00')
