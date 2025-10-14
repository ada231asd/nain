import os
import sys
import json


def ensure_import_path():
    """Make parent package ('utils') importable when running this file directly."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)


def parse_and_explain_borrow_packet(hex_packet: str) -> None:
    """
    Parse a BorrowPowerBank (0x65) packet and print both the parsed structure
    and the human-readable outcome that the server's handler would derive.
    """
    ensure_import_path()

    from utils.packet_utils import parse_borrow_response

    try:
        data = bytes.fromhex(hex_packet)
    except ValueError as e:
        print(f"Invalid hex string: {e}")
        return

    parsed = parse_borrow_response(data)
    print("Parsed packet:")
    print(json.dumps(parsed, ensure_ascii=False, indent=2))

    # Derive the same user-facing message as in BorrowPowerbankHandler
    # Success → 'Повербанк успешно выдан'
    # Failure → reason based on lock status / empty slot, else generic error
    success = bool(parsed.get("Success"))
    slot_number = parsed.get("Slot")
    terminal_id = parsed.get("TerminalID") or "unknown"
    current_slot_locked = int(parsed.get("CurrentSlotLockStatus", 0) or 0)
    adjacent_slot_locked = int(parsed.get("AdjacentSlotLockStatus", 0) or 0)

    if success:
        event_type = "borrow_success"
        message = "Повербанк успешно выдан"
    else:
        event_type = "borrow_failure"
        # Mirror the server's logic for error message selection
        if current_slot_locked:
            message = "Слот заблокирован"
        elif terminal_id == "0000000000000000":
            message = "Слот пуст"
        else:
            message = "Ошибка выдачи повербанка"

    print("\nDerived outcome (what server would broadcast via WS):")
    simulated_ws_payload = {
        "event": "powerbank_borrow_result",
        "type": event_type,
        "message": message,
        "station_id": None,   # unknown in this offline test
        "slot_number": slot_number,
        "order_id": None,
        "powerbank_id": None,
        "user_id": None,
        "terminal_id": terminal_id,
        "current_slot_locked": current_slot_locked,
        "adjacent_slot_locked": adjacent_slot_locked,
    }
    print(json.dumps(simulated_ws_payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    # Example from your log:
    # 001465024F54E21AE002014443484154000016010100
    default_hex = "001465024F54E21AE002014443484154000016010100"

    # Allow overriding via CLI arg
    packet_hex = sys.argv[1] if len(sys.argv) > 1 else default_hex
    print(f"Testing BorrowPowerBank packet (hex): {packet_hex}")
    parse_and_explain_borrow_packet(packet_hex)


