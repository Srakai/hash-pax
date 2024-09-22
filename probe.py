import asyncio
from bleak import BleakClient, BleakScanner, BleakError
from uuid import UUID
import protocol


class PaxDeviceProber:
    # UUIDs for the Device Info and Pax service characteristics
    DeviceInfoService = UUID("0000180A-0000-1000-8000-00805F9B34FB")
    PaxService = UUID("8E320200-64D2-11E6-BDF4-0800200C9A66")
    ManufacturerCharacteristic = UUID("00002A29-0000-1000-8000-00805F9B34FB")
    ModelNumberCharacteristic = UUID("00002A24-0000-1000-8000-00805F9B34FB")
    PaxReadCharacteristic = UUID("8E320201-64D2-11E6-BDF4-0800200C9A66")
    PaxWriteCharacteristic = UUID("8E320202-64D2-11E6-BDF4-0800200C9A66")
    PaxNotifyCharacteristic = UUID("8E320203-64D2-11E6-BDF4-0800200C9A66")

    def __init__(self, device_key):
        self.protocol = protocol.PaxProtocol(device_key)

    async def probe(self, device_address):
        """
        Probe the device, read its characteristics and initialize communication.
        """
        async with BleakClient(device_address) as client:
            # Discover services
            await client.get_services()

            # Discover Pax characteristics
            pax_service = client.services.get_service(self.PaxService)
            if not pax_service:
                raise BleakError("Pax service not found")

            read_char = pax_service.get_characteristic(self.PaxReadCharacteristic)
            write_char = pax_service.get_characteristic(self.PaxWriteCharacteristic)

            print("Pax device discovered, ready for communication.")

            return read_char, write_char

    async def send_message(self, device_address, message: bytes):
        """
        Send a message to the Pax device.
        """
        async with BleakClient(device_address) as client:
            pax_service = client.services.get_service(self.PaxService)
            write_char = pax_service.get_characteristic(self.PaxWriteCharacteristic)

            encrypted_message = self.protocol.encrypt_packet(message)
            await client.write_gatt_char(write_char, encrypted_message)

    async def receive_notification(self, device_address):
        """
        Receive notifications from the Pax device.
        """
        async with BleakClient(device_address) as client:
            pax_service = client.services.get_service(self.PaxService)
            notify_char = pax_service.get_characteristic(self.PaxNotifyCharacteristic)

            await client.start_notify(notify_char, self.notification_handler)

    def notification_handler(self, sender, data):
        """
        Handles notifications from the Pax device.
        """
        decrypted_data = self.protocol.decrypt_packet(data)
        message = self.protocol.handle_incoming_message(decrypted_data)
        print(f"Received: {message}")
