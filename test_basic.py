#!/usr/bin/env python3
"""Basic input test."""


def test_basic_input():
    print("Testing basic Python input...")
    print("Type '1' and press Enter:")

    try:
        choice = input(">>> ")
        print(f"You entered: '{choice}'")

        if choice == "1":
            print("✅ Input working correctly!")
        else:
            print(f"❌ Expected '1', got '{choice}'")

    except Exception as e:
        print(f"❌ Input error: {e}")


if __name__ == "__main__":
    test_basic_input()
