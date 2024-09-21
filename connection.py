import asyncio
from bleak import BleakClient, BleakScanner, BleakError
from uuid import UUID

class PaxDeviceProber:
    # UUIDs for the Device Info Service and characteristics
    DeviceInfoService = UUID("0000180A-0000-1000-8000-00805F9B34FB")
    ManufacturerCharacteristic = UUID("00002A29-0000-1000-8000-00805F9B34FB")
    ModelNumberCharacteristic = UUID("00002A24-0000-1000-8000-00805F9B34FB")

    # Expected values
    ExpectedManufacturer = "PAX Labs, Inc"
    ModelNameEra = "ERA"
    ModelNamePax3 = "PAX3"

    def __init__(self):
        self.states = []

    class ProbeState:
        def __init__(self, device, callback):
            self.device = device
            self.manufacturer = None
            self.model = None
            self.callback = callback

    async def probe(self, device_address, callback):
        """
        Starts probing the device for manufacturer and model information.
        """
        try:
            async with BleakClient(device_address) as client:
                state = self.ProbeState(device_address, callback)
                self.states.append(state)

                # Discover services
                services = await client.get_services()
                print(f"Discovered {len(services)} services")
                print

                # Try to find the Device Info service
                info_service = next((s for s in services if s.uuid == self.DeviceInfoService), None)
                if info_service is None:
                    raise BleakError("Device info service not found")

                print(f"Found Device Info Service: {info_service.uuid}")

                # Discover characteristics of the DeviceInfoService
                manufacturer_char = None
                model_char = None
                for characteristic in info_service.characteristics:
                    if characteristic.uuid == self.ManufacturerCharacteristic:
                        manufacturer_char = characteristic
                    elif characteristic.uuid == self.ModelNumberCharacteristic:
                        model_char = characteristic

                # Check if the characteristics were found
                if manufacturer_char is None or model_char is None:
                    raise BleakError("Manufacturer or Model Number characteristics not found")

                # Read characteristics
                if manufacturer_char:
                    state.manufacturer = (await client.read_gatt_char(manufacturer_char)).decode('utf-8')
                if model_char:
                    state.model = (await client.read_gatt_char(model_char)).decode('utf-8')

                # Probe device information
                await self.perform_probe(client, state)

        except Exception as e:
            self.handle_error(device_address, e, callback)

    async def perform_probe(self, client, state):
        """
        Determine the device type based on manufacturer and model.
        """
        print(f"Determining device type for manufacturer='{state.manufacturer}', model='{state.model}'")

        if state.manufacturer != self.ExpectedManufacturer:
            self.handle_error(state.device, f"Invalid manufacturer: {state.manufacturer}", state.callback)
            return

        if state.model == self.ModelNameEra:
            device = "PaxEraDevice"
            self.handle_success(client, device, state)
        elif state.model == self.ModelNamePax3:
            device = "Pax3Device"
            self.handle_success(client, device, state)
        else:
            self.handle_error(state.device, f"Unsupported device: {state.model}", state.callback)

    def handle_success(self, client, device, state):
        """
        Successfully identified the device, invoke the callback.
        """
        print(f"Device for {state.device}: {device}")
        self.states.remove(state)
        state.callback(device)

    def handle_error(self, device, error, callback):
        """
        Handles errors encountered during the probe process.
        """
        print(f"Probe error for {device}: {error}")
        callback(None, error)

# Example usage:
async def main():
    # Scan for Pax devices
    devices = await BleakScanner.discover()
    pax_device = next((d for d in devices if d.name and "PAX" in d.name), None)

    if pax_device:
        prober = PaxDeviceProber()
        await prober.probe(pax_device.address, lambda device, err: print(f"Probed device: {device}, Error: {err}"))
    else:
        print("No Pax device found")

# Run the async main function
asyncio.run(main())
