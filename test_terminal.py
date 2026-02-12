#!/usr/bin/env python3
"""
Terminal test for AEGIS1 Claude client — text in, text out.
Run: python test_terminal.py

Tests the core Claude + tools pipeline without audio.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from bridge.claude_client import ClaudeClient


async def main():
    print("=" * 60)
    print("  AEGIS1 Terminal Test — Claude + Tools")
    print("=" * 60)
    print("Type your message (or 'quit' to exit)")
    print("Try: 'How did I sleep this week?'")
    print("Try: 'I spent $45 on lunch'")
    print("Try: 'Analyze my sleep and mood patterns'")
    print("=" * 60)

    client = ClaudeClient()

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break

        print("\nAegis: ", end="", flush=True)
        async for chunk in client.get_response(user_input):
            print(chunk, end="", flush=True)
        print()


if __name__ == "__main__":
    asyncio.run(main())
