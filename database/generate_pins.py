"""
Regenerates random per-detective PINs and prints ready-to-paste SQL UPDATE statements.

Run before a real event to replace the placeholder PINs committed in seed.sql
(those are fine for local dev, but shouldn't be reused as real event credentials
since they're sitting in source control). Hand each printed PIN to its detective
along with their username -- organizers should record and distribute these
out-of-band (e.g. printed slips), not via seed.sql itself.

Usage:
    python database/generate_pins.py --count 30 > pins_for_event.sql
    # then run the printed statements against the target database, and
    # separately print/hand out the PIN column to participants.
"""

import argparse
import secrets


def generate_pin() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def main():
    parser = argparse.ArgumentParser(description="Generate fresh per-detective PINs")
    parser.add_argument("--count", type=int, default=30, help="Number of DETECTIVE-NN accounts")
    args = parser.parse_args()

    seen = set()
    for i in range(1, args.count + 1):
        username = f"DETECTIVE-{i:02d}"
        pin = generate_pin()
        while pin in seen:
            pin = generate_pin()
        seen.add(pin)
        print(f"UPDATE game.participants SET pin = '{pin}' WHERE username = '{username}';  -- handout PIN: {pin}")


if __name__ == "__main__":
    main()
