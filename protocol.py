import struct
from enum import Enum

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

# Utility functions for encoding and decoding
def encode_bitmask(attributes):
    bitmask = 0
    for attr in attributes:
        if attr.value <= 63:
            bitmask |= (1 << attr.value)
    return struct.pack('>BQ', PaxMessageType.StatusUpdate.value, bitmask)

def decode_bitmask(data):
    if len(data) < 9:
        raise ValueError("Data too small for StatusUpdateMessage")
    bitmask = struct.unpack('>Q', data[1:9])[0]
    return {PaxMessageType(attr) for attr in range(64) if (bitmask & (1 << attr))}

def encode_temperature_message(message_type, temperature):
    temp_encoded = int(temperature * 10)
    return struct.pack('>BH', message_type.value, temp_encoded)

def decode_temperature_message(data):
    if len(data) < 3:
        raise ValueError("Data too small for TemperatureMessage")
    temp_encoded = struct.unpack('>H', data[1:3])[0]
    return temp_encoded / 10.0

# Encoding and Decoding Functions for Specific Messages
def encode_lock_state(is_locked):
    return struct.pack('BB', PaxMessageType.LockStatus.value, 1 if is_locked else 0)

def decode_lock_state(data):
    if len(data) < 2:
        raise ValueError("Data too small for LockStateMessage")
    return data[1] != 0

def encode_dynamic_mode(mode):
    return struct.pack('BB', PaxMessageType.DynamicMode.value, mode.value)

def decode_dynamic_mode(data):
    if len(data) < 2:
        raise ValueError("Data too small for DynamicModeMessage")
    mode = data[1]
    return DynamicMode(mode)

# Mode Enum for Dynamic Mode
class DynamicMode(Enum):
    Standard = 0
    Boost = 1
    Efficiency = 2
    Stealth = 3
    Flavor = 4

# Message Handling
def handle_message(data):
    message_type = PaxMessageType(data[0])
    
    if message_type == PaxMessageType.Battery:
        return f"Battery Level: {data[1]}%"
    
    elif message_type == PaxMessageType.LockStatus:
        is_locked = decode_lock_state(data)
        return f"Device is {'Locked' if is_locked else 'Unlocked'}"
    
    elif message_type == PaxMessageType.HeaterSetPoint or message_type == PaxMessageType.ActualTemp:
        temperature = decode_temperature_message(data)
        return f"Temperature: {temperature}°C"

    elif message_type == PaxMessageType.DynamicMode:
        mode = decode_dynamic_mode(data)
        return f"Dynamic Mode: {mode.name}"

    elif message_type == PaxMessageType.SupportedAttributes:
        supported_attrs = decode_bitmask(data)
        return f"Supported Attributes: {', '.join([attr.name for attr in supported_attrs])}"

    elif message_type == PaxMessageType.ChargeStatus:
        is_charging = (data[1] & 0x01) != 0
        charge_complete = (data[1] & 0x02) != 0
        return f"Charging: {is_charging}, Charge Complete: {charge_complete}"

    else:
        return f"Unhandled message type: {message_type}"
