import asyncio
import os
import time
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "7e2f6a91-8c3d-4b2a-9f6e-1c4d8a7b5e92"
CHARACTERISTIC_UUID = "a1b2c3d4-1234-5678-abcd-a1b2c3d4e5f6"

# --- ASCII Art ---
walking_man = [
    r"""
    \ O /
     \|/
     / 
    """,
    r"""
     O
    /|
    / 
    """
]

stop_hand = r"""
      .--.
     |o_o |
     |:_/ |
    //   \ 
   (|     | )
  / \_   _/ 
  \___)=(___/
"""

def display_art(pir_status, frame_index):
    """Display ASCII art based on PIR status"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    if pir_status == "1":
        print("Movement Detected!")
        print(walking_man[frame_index % len(walking_man)])
    else:
        print("No Movement")
        print(stop_hand)

async def scan_for_esp32():
    """Scan for BLE devices with longer timeout"""
    print("Scanning for BLE devices...")

    found_device = False
    while not found_device:
        devices = await BleakScanner.discover(timeout=1.0, return_adv=True)
        
        print(f"\nFound {len(devices)} devices:")
        esp32_address = None
        
        for address, (device, adv_data) in devices.items():
            name = device.name if device.name else "None"
            # print(f"  {name:20s} {address}")
            
            # Check if this is ESP32_PIR
            if device.name and "ESP32_PIR" in device.name:
                esp32_address = address
                found_device = True
    
    return esp32_address

async def connect_and_read(address):
    """Connect to ESP32 and read the characteristic"""
    try:
        print(f"\nConnecting to {address}...")
        async with BleakClient(address, timeout=10.0) as client:
            print(f"Connected")
            
            frame_index = 0
            while True:
                # Read the characteristic
                value = await client.read_gatt_char(CHARACTERISTIC_UUID)
                pir_status = value.decode('utf-8')
                
                display_art(pir_status, frame_index)
                
                if pir_status == "1":
                    frame_index += 1
                
                await asyncio.sleep(0.2)  # Wait before reading again
            
    except Exception as e:
        print(f"Error: {e}")

async def main():
    address = await scan_for_esp32()
    
    if address:
        await connect_and_read(address)
    else:
        print("\n✗ ESP32_PIR not found.")

if __name__ == "__main__":
    asyncio.run(main())
