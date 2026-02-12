"""
AEGIS1 CLI — Voice health & wealth assistant.

Entry point: `python -m aegis` or `aegis` (after pip install -e .)
"""

import click
import asyncio
import sys
from pathlib import Path
from typing import Optional

from aegis.config import settings


@click.group()
@click.version_option(version="0.1.0")
def main():
    """AEGIS1 — AI voice pendant for health & wealth management."""
    pass


@main.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, help="Server port")
def serve(host: str, port: int):
    """Start WebSocket bridge server."""
    import uvicorn
    from aegis.main import app

    click.echo(f"🚀 Starting AEGIS1 Bridge on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


@main.command()
def terminal():
    """Interactive terminal client (text-only)."""
    import websockets
    import json

    click.echo("🎤 AEGIS1 Terminal Client")
    click.echo("Type your question or 'exit' to quit\n")

    async def run_client():
        uri = f"ws://localhost:{settings.bridge_port}/ws/text"
        try:
            async with websockets.connect(uri) as websocket:
                while True:
                    user_input = click.prompt("You", default="")
                    if user_input.lower() in ("exit", "quit"):
                        click.echo("👋 Goodbye!")
                        break
                    if not user_input:
                        continue

                    # Send message
                    await websocket.send(json.dumps({"message": user_input}))

                    # Receive streaming response
                    click.echo("\nAEGIS1: ", nl=False)
                    while True:
                        try:
                            msg = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                            data = json.loads(msg)
                            if data.get("type") == "chunk":
                                click.echo(data.get("text", ""), nl=False)
                            elif data.get("type") == "done":
                                click.echo("\n")
                                break
                        except asyncio.TimeoutError:
                            click.echo("\n")
                            break
        except ConnectionRefusedError:
            click.echo(
                f"❌ Could not connect to server at {uri}\n"
                f"   Start the server first: aegis serve",
                err=True,
            )
            sys.exit(1)

    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        click.echo("\n👋 Interrupted by user")


@main.command()
@click.argument("xml_path", type=click.Path(exists=True))
def import_health(xml_path: str):
    """Import Apple Health XML export."""
    from pathlib import Path

    xml_file = Path(xml_path)
    if not xml_file.exists():
        click.echo(f"❌ File not found: {xml_path}", err=True)
        sys.exit(1)

    click.echo(f"📥 Importing Apple Health data from {xml_file.name}")
    click.echo("   ⏳ This feature will be implemented in Phase 2")
    # TODO: Implement parse_and_load from aegis.health_import


@main.command()
def seed():
    """Seed database with demo data."""
    import asyncio

    async def seed_data():
        from aegis.db import init_db

        click.echo("🌱 Seeding database with demo data...")
        await init_db()
        click.echo("✅ Demo data loaded")

    try:
        asyncio.run(seed_data())
    except Exception as e:
        click.echo(f"❌ Error seeding database: {e}", err=True)
        sys.exit(1)


@main.command()
def health():
    """Health check — verify server connectivity."""
    import httpx

    url = f"http://localhost:{settings.bridge_port}/health"
    try:
        resp = httpx.get(url, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            click.echo(f"✅ Server healthy: {data}")
        else:
            click.echo(f"⚠️  Server returned {resp.status_code}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(
            f"❌ Server not running at {url}\n"
            f"   Start it with: aegis serve",
            err=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
