import asyncio
import traceback
import os
import logging
from bleak import BleakClient, BleakScanner, BleakError
from bleak.backends.device import BLEDevice

SERVICE_UUID        = "7e2f6a91-8c3d-4b2a-9f6e-1c4d8a7b5e92"
CHARACTERISTIC_UUID = "a1b2c3d4-1234-5678-abcd-a1b2c3d4e5f6"

CSV_PATH            = "pir_output.csv"
RECONNECT_DELAY     = 3.0   # seconds between reconnect attempts
SCAN_TIMEOUT        = 30.0  # seconds to wait during BLE scan

# BlueZ adapter to use on Linux (e.g. "hci0", "hci1").
BLE_ADAPTER         = os.getenv("BLE_ADAPTER", "hci1")


def _configure_logging() -> None:
    """Enable verbose Bleak/DBus logging when BLEAK_DEBUG is set."""
    if os.getenv("BLEAK_DEBUG"):
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("bleak").setLevel(logging.DEBUG)


def _adapter_exists(adapter: str) -> bool:
    # Linux/BlueZ adapters show up as /sys/class/bluetooth/hciX
    return os.path.isdir(f"/sys/class/bluetooth/{adapter}")


def resolve_ble_adapter(preferred: str) -> str:
    """Return a usable adapter name; fall back to hci0 when preferred is missing."""
    if _adapter_exists(preferred):
        return preferred

    if preferred != "hci0" and _adapter_exists("hci0"):
        print(f"Adapter '{preferred}' not found; falling back to 'hci0'")
        return "hci0"

    try:
        candidates = sorted(
            d for d in os.listdir("/sys/class/bluetooth") if d.startswith("hci")
        )
    except FileNotFoundError:
        candidates = []

    if candidates:
        print(f"Adapter '{preferred}' not found; using '{candidates[0]}'")
        return candidates[0]

    # Nothing to validate against (non-Linux or /sys not mounted). Keep preferred.
    return preferred


# ── Scanner ───────────────────────────────────────────────────────────────────

async def scan_for_esp32(adapter: str = BLE_ADAPTER) -> BLEDevice | None:
    print(f"Scanning for ESP32 via BLE (adapter={adapter})...")
    found = asyncio.Event()
    found_device: BLEDevice | None = None

    def on_detection(device, adv_data):
        nonlocal found_device
        if adv_data and adv_data.service_uuids:
            if SERVICE_UUID.lower() in [s.lower() for s in adv_data.service_uuids]:
                print(f"✓ Found ESP32: {device.address}")
                found_device = device
                found.set()

    scanner = BleakScanner(on_detection, bluez={"adapter": adapter})
    started = False
    try:
        await scanner.start()
        started = True
        await asyncio.wait_for(found.wait(), timeout=SCAN_TIMEOUT)
    except BleakError as e:
        print(f"BLE scan error (adapter={adapter}): {e}")
        if adapter != "hci0":
            print("Falling back to adapter 'hci0' and re-scanning")
            return await scan_for_esp32(adapter="hci0")
    except asyncio.TimeoutError:
        print("✗ Scan timed out — is the ESP32 advertising?")
    finally:
        if started:
            await scanner.stop()

    return found_device


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

async def run_client(device: BLEDevice, adapter: str = BLE_ADAPTER):
    """
    Connects, subscribes to notifications, and keeps reconnecting
    whenever the link drops.
    """
    last_state = [None]   # mutable container for the closure

    while True:
        try:
            print(f"\nConnecting to {device.address} (adapter={adapter})...")
            async with BleakClient(device, timeout=20.0, bluez={"adapter": adapter}) as client:
                print("Connected — subscribing to notifications")

                await client.start_notify(
                    CHARACTERISTIC_UUID,
                    make_notify_handler(last_state)
                )

                # Block here until the connection drops
                while client.is_connected:
                    await asyncio.sleep(0.5)

                print("Connection lost")

        except (asyncio.TimeoutError, TimeoutError, asyncio.CancelledError):
            # On BlueZ (common on Raspberry Pi), a timeout here is often caused by
            # stale device state or private address rotation. Re-scan to refresh.
            print("Connection timed out — re-scanning before retry")
            rescanned = await scan_for_esp32(adapter=adapter)
            if rescanned is not None:
                device = rescanned

        except BleakError as e:
            print(f"BLE error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            traceback.print_exc()

        print(f"Retrying in {RECONNECT_DELAY}s...")
        await asyncio.sleep(RECONNECT_DELAY)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    _configure_logging()

    adapter = resolve_ble_adapter(BLE_ADAPTER)
    device = await scan_for_esp32(adapter=adapter)
    if device:
        await run_client(device, adapter=adapter)
    else:
        print("✗ ESP32_PIR not found.")

if __name__ == "__main__":
    asyncio.run(main())