import asyncio
import json
import websockets

async def listen():
    """Connects to the WebSocket and prints received messages."""
    uri = "ws://127.0.0.1:8000/ws"
    print(f"Attempting to connect to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Successfully connected to WebSocket. Waiting for messages...")
            try:
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"RECEIVED: {data}")
                    if data.get("status") in ["complete", "stopped", "error"]:
                        print("Processing finished. Closing connection.")
                        break
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by server.")
    except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError) as e:
        print(f"Could not connect to WebSocket: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(listen())
    except KeyboardInterrupt:
        print("\nClient stopped.")
