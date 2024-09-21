import asyncio
import argparse
from probe import PaxDeviceProber
import protocol
from bleak import BleakClient, BleakScanner

async def probe_device():
    """
    Probes the Pax device and prints the result.
    """
    devices = await BleakScanner.discover()
    pax_device = next((d for d in devices if d.name and "PAX" in d.name), None)

    if pax_device:
        prober = PaxDeviceProber()
        await prober.probe(pax_device.address, lambda device, err: print(f"Probed device: {device}, Error: {err}"))
    else:
        print("No Pax device found")

async def send_lock_command(device_address, lock):
    """
    Sends a lock or unlock command to the Pax device.
    """
    async with BleakClient(device_address) as client:
        lock_msg = protocol.encode_lock_state(is_locked=lock)
        await client.write_gatt_char(PaxDeviceProber.LockCharacteristic, lock_msg)
        print(f"Sent {'lock' if lock else 'unlock'} command to device")

async def send_temperature_command(device_address, temperature):
    """
    Sends a temperature set point command to the Pax device.
    """
    async with BleakClient(device_address) as client:
        temp_msg = protocol.encode_temperature_message(protocol.PaxMessageType.HeaterSetPoint, temperature)
        await client.write_gatt_char(PaxDeviceProber.HeaterCharacteristic, temp_msg)
        print(f"Set temperature to {temperature}°C")

async def get_battery_status(device_address):
    """
    Requests the battery status from the Pax device.
    """
    async with BleakClient(device_address) as client:
        battery_msg = await client.read_gatt_char(PaxDeviceProber.BatteryCharacteristic)
        battery_level = protocol.handle_message(battery_msg)
        print(f"Battery Level: {battery_level}")

async def cli():
    """
    Main CLI function that handles user input.
    """
    parser = argparse.ArgumentParser(description="Pax Device CLI")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Probe command
    probe_parser = subparsers.add_parser("probe", help="Probe the Pax device")

    # Lock/Unlock command
    lock_parser = subparsers.add_parser("lock", help="Lock or unlock the Pax device")
    lock_parser.add_argument("--lock", action="store_true", help="Lock the device")
    lock_parser.add_argument("--unlock", action="store_true", help="Unlock the device")
    lock_parser.add_argument("--address", required=True, help="Bluetooth address of the Pax device")

    # Set temperature command
    temp_parser = subparsers.add_parser("set-temp", help="Set the oven temperature")
    temp_parser.add_argument("--temp", type=float, required=True, help="Temperature in °C")
    temp_parser.add_argument("--address", required=True, help="Bluetooth address of the Pax device")

    # Get battery status command
    battery_parser = subparsers.add_parser("battery", help="Get the battery level")
    battery_parser.add_argument("--address", required=True, help="Bluetooth address of the Pax device")

    args = parser.parse_args()

    # Handle each command
    if args.command == "probe":
        await probe_device()
    elif args.command == "lock":
        if args.lock:
            await send_lock_command(args.address, lock=True)
        elif args.unlock:
            await send_lock_command(args.address, lock=False)
    elif args.command == "set-temp":
        await send_temperature_command(args.address, args.temp)
    elif args.command == "battery":
        await get_battery_status(args.address)
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(cli())
