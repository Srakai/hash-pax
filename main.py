import asyncio
import argparse
from bleak import BleakClient, BleakScanner
import protocol

class PaxDevice:
    def __init__(self, device_key):
        self.device_key = device_key
        self.client = None
        self.read_characteristic = None
        self.write_characteristic = None
        self.notify_characteristic = None
        self.serial_number = None

    async def connect(self, address):
        """
        Connects to the Pax device and initializes the necessary characteristics.
        """
        self.client = BleakClient(address)
        await self.client.connect()
        print(f"Connected to Pax device at {address}")
        
        # Discover services and characteristics
        await self.discover_services()

    async def discover_services(self):
        """
        Discover the necessary services and characteristics, including reading device info characteristics.
        """
        services = await self.client.get_services()

        info_service = None
        pax_service = None

        # Find the Device Info Service and Pax Service
        for service in services:
            if service.uuid == str(protocol.DEVICE_INFO_SERVICE):
                info_service = service
            elif service.uuid == str(protocol.PAX_SERVICE):
                pax_service = service

        if not info_service or not pax_service:
            raise Exception(f"Failed to find required services: {info_service}, {pax_service}")

        # Discover characteristics for the device info service
        await self.discover_device_info(info_service)
        
        # Discover characteristics for the Pax service
        await self.discover_pax_service(pax_service)

    async def discover_device_info(self, info_service):
        """
        Discover and read the Manufacturer, Model, Serial, HW, and SW version from the Device Info Service.
        """
        for char in info_service.characteristics:
            if char.uuid == str(protocol.MANUFACTURER_CHARACTERISTIC):
                manufacturer = await self.client.read_gatt_char(char)
                print(f"Manufacturer: {manufacturer.decode()}")
            elif char.uuid == str(protocol.MODEL_NUMBER_CHARACTERISTIC):
                model_number = await self.client.read_gatt_char(char)
                print(f"Model Number: {model_number.decode()}")
            elif char.uuid == str(protocol.SERIAL_NUMBER_CHARACTERISTIC):
                serial_number = await self.client.read_gatt_char(char)
                self.serial_number = serial_number.decode()
                print(f"Serial Number: {self.serial_number}")
            elif char.uuid == str(protocol.HW_REV_CHARACTERISTIC):
                hw_rev = await self.client.read_gatt_char(char)
                print(f"Hardware Revision: {hw_rev.decode()}")
            elif char.uuid == str(protocol.SW_REV_CHARACTERISTIC):
                sw_rev = await self.client.read_gatt_char(char)
                print(f"Software Revision: {sw_rev.decode()}")

        # Derive the shared encryption key using the serial number
        if self.serial_number:
            self.device_key = protocol.derive_shared_key(self.serial_number)
            print(f"Derived Device Key: {self.device_key.hex()}")

    async def discover_pax_service(self, pax_service):
        """
        Discover the Pax read, write, and notify characteristics.
        """
        for char in pax_service.characteristics:
            if char.uuid == str(protocol.PAX_READ_CHARACTERISTIC):
                self.read_characteristic = char
            elif char.uuid == str(protocol.PAX_WRITE_CHARACTERISTIC):
                self.write_characteristic = char
            elif char.uuid == str(protocol.PAX_NOTIFY_CHARACTERISTIC):
                self.notify_characteristic = char

        if not all([self.read_characteristic, self.write_characteristic, self.notify_characteristic]):
            raise Exception("Failed to find required Pax service characteristics")

        # Enable notifications for the notify characteristic
        await self.client.start_notify(self.notify_characteristic, self.notification_handler)
        print("Notifications enabled.")

    async def notification_handler(self, sender, data):
        """
        Handler for receiving notifications from the device.
        After receiving a notification, it will trigger a read from the read characteristic.
        """
        #print(f"Notification received from {sender}. Triggering a read.")
        try:
            # Read from the Pax read characteristic
            encrypted_data = await self.client.read_gatt_char(self.read_characteristic)
            decrypted_data = protocol.decrypt_packet(encrypted_data, self.device_key)
            #print(f"Decrypted data: {decrypted_data.hex()}")
            await self.process_packet(decrypted_data)
        except Exception as e:
            print(f"Error processing notification: {e}")

    async def process_packet(self, decrypted_data):
        """
        Process received packets and handle the appropriate message type.
        """
        data = protocol.handle_incoming_message(decrypted_data)
        print(f"Received: {data}")

    async def send_message(self, message):
        """
        Encrypt and send a message to the device.
        """
        encrypted_message = protocol.encrypt_packet(message, self.device_key)
        print(f"Sending message: {encrypted_message.hex()}")
        await self.client.write_gatt_char(self.write_characteristic, encrypted_message, response=False)

    async def disconnect(self):
        await self.client.disconnect()
        print("Disconnected from the Pax device.")

# Utility Functions for CLI Commands

async def probe_device():
    """
    Scan and connect to the Pax device.
    """
    try:
        devices = await BleakScanner.discover()
    except Exception as e:
        print(f"Error discovering devices: {e}")
        return

    if devices is None or len(devices) == 0:
        print("No devices found.")
        return

    # Check if any device has 'PAX' in its name
    pax_device = next((d for d in devices if d.name and "PAX" in d.name), None)

    if pax_device:
        print(f"Found Pax device: {pax_device.name}")
        print(f"Address: {pax_device.address}")
        device = PaxDevice(protocol.DEVICE_KEY_KEY)
        await device.connect(pax_device.address)
        await device.disconnect()
    else:
        print("No Pax device found.")

async def lock_device(address, lock):
    """
    Lock or unlock the Pax device.
    """
    device = PaxDevice(protocol.DEVICE_KEY_KEY)
    await device.connect(address)
    
    lock_message = protocol.encode_lock_message(lock)
    await device.send_message(lock_message)
    
    print(f"Sent {'lock' if lock else 'unlock'} command.")
    await device.disconnect()

async def set_temperature(address, temperature):
    """
    Set the temperature of the Pax device.
    """
    device = PaxDevice(protocol.DEVICE_KEY_KEY)
    await device.connect(address)
    
    temp_message = protocol.encode_temperature_message(temperature)
    await device.send_message(temp_message)

    status_message = protocol.encode_status_update_message({protocol.PaxMessageType.HeaterSetPoint})
    await device.send_message(status_message)
    
    print(f"Set temperature to {temperature}°C.")
    
    # Keep receiving notifications
    while True:
        await asyncio.sleep(1)

async def receive_notifications(address):
    """
    Receive notifications from the Pax device.
    """
    device = PaxDevice(protocol.DEVICE_KEY_KEY)
    await device.connect(address)
    
    # Keep receiving notifications (no disconnect here)
    print("Receiving notifications... Press Ctrl+C to exit.")
    while True:
        await asyncio.sleep(1)

# CLI Implementation

async def cli():
    parser = argparse.ArgumentParser(description="Pax Device CLI")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Probe command
    subparsers.add_parser("probe", help="Probe the Pax device")

    # Lock/Unlock command
    lock_parser = subparsers.add_parser("lock", help="Lock or unlock the Pax device")
    lock_parser.add_argument("--lock", action="store_true", help="Lock the device")
    lock_parser.add_argument("--unlock", action="store_true", help="Unlock the device")
    lock_parser.add_argument("--address", required=True, help="Bluetooth address of the Pax device")

    # Set temperature command
    temp_parser = subparsers.add_parser("set-temp", help="Set the oven temperature")
    temp_parser.add_argument("--temp", type=float, required=True, help="Temperature in °C")
    temp_parser.add_argument("--address", required=True, help="Bluetooth address of the Pax device")

    # Receive notifications
    notif_parser = subparsers.add_parser("notify", help="Receive notifications from the device")
    notif_parser.add_argument("--address", required=True, help="Bluetooth address of the Pax device")

    args = parser.parse_args()

    if args.command == "probe":
        await probe_device()
    elif args.command == "lock":
        await lock_device(args.address, lock=args.lock)
    elif args.command == "set-temp":
        await set_temperature(args.address, args.temp)
    elif args.command == "notify":
        await receive_notifications(args.address)
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(cli())
