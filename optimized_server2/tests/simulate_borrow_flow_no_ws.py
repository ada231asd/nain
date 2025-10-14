import os
import sys
import asyncio
import json
import struct


def ensure_import_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)


def build_borrow_response_packet(slot: int, result_code: int, terminal_id_ascii_or_hex: str,
                                 current_slot_locked: int = 0, adjacent_slot_locked: int = 0, vsn: int = 2) -> bytes:
    """Build a synthetic BorrowPowerBank response (0x65) packet matching parser expectations.
    Header: >H B B B I  (len, cmd, vsn, checksum, token)
    Payload: slot(1), result(1), terminal_id(8), current_slot_locked(1), adjacent_slot_locked(1)
    """
    ensure_import_path()
    from utils.packet_utils import compute_checksum

    # Build terminal_id 8 bytes: if ascii-like (4 chars + 4 bytes hex), accept; else interpret as hex string of 8 bytes
    term_bytes = b""
    try:
        # Try to accept as 8 raw hex bytes (16 hex chars)
        raw = bytes.fromhex(terminal_id_ascii_or_hex)
        if len(raw) == 8:
            term_bytes = raw
        else:
            raise ValueError("terminal_id hex must be 8 bytes")
    except ValueError:
        # Fallback: first 4 ascii chars, next 4 bytes from hex
        ascii_part = terminal_id_ascii_or_hex[:4].encode('ascii', errors='ignore')
        hex_tail = terminal_id_ascii_or_hex[4:]
        try:
            tail_bytes = bytes.fromhex(hex_tail)
        except Exception:
            tail_bytes = b"\x00\x00\x00\x00"
        ascii_part = (ascii_part + b"\x00\x00\x00\x00")[:4]
        tail_bytes = (tail_bytes + b"\x00\x00\x00\x00")[:4]
        term_bytes = ascii_part + tail_bytes

    payload = struct.pack(
        ">BB8sBB",
        int(slot) & 0xFF,
        int(result_code) & 0xFF,
        term_bytes,
        int(current_slot_locked) & 0xFF,
        int(adjacent_slot_locked) & 0xFF,
    )
    checksum = compute_checksum(payload)
    token = 0x12345678
    header = struct.pack(
        ">H B B B I",
        7 + len(payload),
        0x65,
        int(vsn) & 0xFF,
        checksum & 0xFF,
        token,
    )
    return header + payload


class FakeConnection:
    def __init__(self, station_id: int):
        self.station_id = station_id
        self.secret_key = "dummy"
        self.writer = None


async def main():
    ensure_import_path()
    # Import after path setup
    from handlers.borrow_powerbank import BorrowPowerbankHandler
    from models import station_powerbank as sp_module

    # Monkeypatch DB-facing methods so test does not need a real DB
    async def fake_get_by_slot(db_pool, station_id, slot_number):
        class Obj:
            powerbank_id = 1
        return Obj()

    async def fake_remove_powerbank(db_pool, station_id, slot_number):
        return True

    sp_module.StationPowerbank.get_by_slot = staticmethod(fake_get_by_slot)
    sp_module.StationPowerbank.remove_powerbank = staticmethod(fake_remove_powerbank)

    # Patch Station methods used for last_seen and remain_num
    from models import station as station_module

    class FakeStation:
        def __init__(self):
            self.remain_num = 5

        async def update_last_seen(self, db_pool):
            return True

        async def update_remain_num(self, db_pool, new_value: int):
            self.remain_num = new_value
            return True

    async def fake_get_station_by_id(db_pool, station_id):
        return FakeStation()

    station_module.Station.get_by_id = staticmethod(fake_get_station_by_id)

    # Create handler with fake pool and connection manager
    handler = BorrowPowerbankHandler(db_pool=None, connection_manager=None)

    # Create a pending request as if send_borrow_request_and_wait was called
    loop = asyncio.get_running_loop()
    order_id = 42
    station_id = 101
    slot_number = 2
    future = loop.create_future()
    handler.pending_requests[order_id] = {
        'future': future,
        'station_id': station_id,
        'slot_number': slot_number,
        'powerbank_id': 1,
        'user_id': 777,
    }

    # Build a success packet for the same slot
    success_packet = build_borrow_response_packet(
        slot=slot_number,
        result_code=1,
        terminal_id_ascii_or_hex="DCHA54000016",
        current_slot_locked=1,
        adjacent_slot_locked=1,
        vsn=2,
    )

    print("Simulating SUCCESS flow...")
    await handler.handle_borrow_response(success_packet, FakeConnection(station_id))
    result = await future
    print("API would return:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Now simulate failure (slot locked)
    order_id_fail = 43
    future_fail = loop.create_future()
    handler.pending_requests[order_id_fail] = {
        'future': future_fail,
        'station_id': station_id,
        'slot_number': slot_number,
        'powerbank_id': 1,
        'user_id': 777,
    }
    failure_packet = build_borrow_response_packet(
        slot=slot_number,
        result_code=0,
        terminal_id_ascii_or_hex="DCHA54000016",
        current_slot_locked=1,
        adjacent_slot_locked=0,
        vsn=2,
    )

    print("\nSimulating FAILURE flow (slot locked)...")
    await handler.handle_borrow_response(failure_packet, FakeConnection(station_id))
    result_fail = await future_fail
    print("API would return:")
    print(json.dumps(result_fail, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())


