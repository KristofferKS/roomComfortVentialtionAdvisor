import asyncio
import traceback
from bleak import BleakClient, BleakScanner, BleakError

SERVICE_UUID        = "7e2f6a91-8c3d-4b2a-9f6e-1c4d8a7b5e92"
CHARACTERISTIC_UUID = "a1b2c3d4-1234-5678-abcd-a1b2c3d4e5f6"

CSV_PATH            = "pir_output.csv"
RECONNECT_DELAY     = 3.0   # seconds between reconnect attempts
SCAN_TIMEOUT        = 30.0  # seconds to wait during BLE scan


# ── Scanner ───────────────────────────────────────────────────────────────────

async def scan_for_esp32() -> str | None:
    print("Scanning for ESP32 via BLE...")
    found = asyncio.Event()
    address = None

    def on_detection(device, adv_data):
        nonlocal address
        if adv_data and adv_data.service_uuids:
            if SERVICE_UUID.lower() in [s.lower() for s in adv_data.service_uuids]:
                print(f"✓ Found ESP32: {device.address}")
                address = device.address
                found.set()

    scanner = BleakScanner(on_detection)
    await scanner.start()
    try:
        await asyncio.wait_for(found.wait(), timeout=SCAN_TIMEOUT)
    except asyncio.TimeoutError:
        print("✗ Scan timed out — is the ESP32 advertising?")
    finally:
        await scanner.stop()

    return address


# ── Notification handler ──────────────────────────────────────────────────────

def make_notify_handler(last_state: list):
    """
    Returns a callback for start_notify.
    last_state is a 1-element list so the closure can mutate it.
    """
    def handler(sender, data: bytearray):
        value = data.decode("utf-8").strip()
        if value != last_state[0]:
            last_state[0] = value
            print(f"PIR Status: {value}")
            with open(CSV_PATH, "w") as f:
                f.write(value)
    return handler


# ── Connection loop ───────────────────────────────────────────────────────────

async def run_client(address: str):
    """
    Connects, subscribes to notifications, and keeps reconnecting
    whenever the link drops.
    """
    last_state = [None]   # mutable container for the closure

    while True:
        print(f"\nConnecting to {address}...")
        try:
            async with BleakClient(address, timeout=10.0) as client:
                print("Connected — subscribing to notifications")

                await client.start_notify(
                    CHARACTERISTIC_UUID,
                    make_notify_handler(last_state)
                )

                # Block here until the connection drops
                while client.is_connected:
                    await asyncio.sleep(0.5)

                print("Connection lost")

        except BleakError as e:
            print(f"BLE error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            traceback.print_exc()

        print(f"Retrying in {RECONNECT_DELAY}s...")
        await asyncio.sleep(RECONNECT_DELAY)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    address = await scan_for_esp32()
    if address:
        await run_client(address)
    else:
        print("✗ ESP32_PIR not found.")

if __name__ == "__main__":
    asyncio.run(main())