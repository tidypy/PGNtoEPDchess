import asyncio
import json
import websockets
import httpx
import os
import sys

# Sample settings for the test job
# NOTE: This script will create a small test PGN file for you.
TEST_PGN_FILE = "test_games.pgn"
TEST_SETTINGS = {
    "pgn_input_file": TEST_PGN_FILE,
    "output_file": "test_output.epd",
    "min_ply": 10,
    "max_ply": 30,
    "min_elo": 2000,
    "eco_prefix": "C",
    "workers": 2,
}

async def start_job():
    """
    Waits a moment, then sends a POST request to start processing.
    Returns True on success, False on failure.
    """
    await asyncio.sleep(1) # Give the listener time to connect
    print("\n--- Sending start request ---")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://127.0.0.1:8000/start", json=TEST_SETTINGS, timeout=5.0)
            response.raise_for_status()
            server_response = response.json()
            print(f"Start request sent. Server responded: {server_response}")
            if server_response.get("status") == "error":
                print(f"!!! Server returned an error on start: {server_response.get('message')}")
                return False
            return True
    except httpx.RequestError as e:
        print(f"Error sending start request: {e}")
        return False

async def listen_and_run():
    """
    Connects to the WebSocket, starts the job, and prints messages.
    Returns True if the test completes successfully, False otherwise.
    """
    uri = "ws://127.0.0.1:8000/ws"
    print(f"Attempting to connect to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Successfully connected to WebSocket.")
            
            job_started = await start_job()
            if not job_started:
                print("\n--- TEST FAILED: Could not start processing job. ---")
                return False

            # Listen for messages
            print("--- Waiting for messages from server ---")
            try:
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"RECEIVED: {data}")
                    status = data.get("status")
                    if status == "error":
                        print(f"\n--- TEST FAILED: Received error status: {data.get('message')} ---")
                        return False
                    if status in ["complete", "stopped"]:
                        print("\n--- TEST PASSED: Processing finished successfully. ---")
                        return True
            except websockets.exceptions.ConnectionClosed:
                print("\n--- TEST FAILED: Connection closed unexpectedly by server. ---")
                return False

    except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError) as e:
        print(f"Could not connect to WebSocket: {e}")
        print("Please ensure the backend server is running with 'run-backend.sh'")
        return False

def setup_test_pgn():
    """Creates a small PGN file for testing if it doesn't exist."""
    if not os.path.exists(TEST_PGN_FILE):
        print(f"Creating dummy PGN file: {TEST_PGN_FILE}")
        with open(TEST_PGN_FILE, "w") as f:
            f.write("""
[Event "Test Game 1"]
[ECO "C41"]
[WhiteElo "2100"]
[BlackElo "2200"]
1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5 4. d4 Nf6 5. Nf3 Bf5 6. Bc4 e6 7. Bd2 c6 8. Nd5 Qd8 9. Nxf6+ Qxf6 10. Qe2 Bg4 11. O-O-O Bxf3 12. gxf3 Nd7 *

[Event "Test Game 2"]
[ECO "A01"]
[WhiteElo "1900"]
[BlackElo "1950"]
1. b3 e5 2. Bb2 Nc6 *
""")

if __name__ == "__main__":
    setup_test_pgn()
    try:
        success = asyncio.run(listen_and_run())
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nClient stopped.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)
