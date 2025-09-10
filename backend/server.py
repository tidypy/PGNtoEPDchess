import asyncio
import multiprocessing
from typing import Dict, Any, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from processor import run_processing

app = FastAPI()

# Allow CORS for the Svelte frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# --- State Management ---
# These need to be managed carefully in a multiprocessing context.
# Using Manager to create shared objects between processes.
process_manager = multiprocessing.Manager()
pause_event = process_manager.Event()
stop_event = process_manager.Event()

# A queue to get progress updates from the background process
progress_queue = process_manager.Queue()

background_process = None

async def progress_broadcaster():
    """Task to listen to the queue and broadcast updates."""
    while True:
        try:
            if not progress_queue.empty():
                message = progress_queue.get_nowait()
                await manager.broadcast(message)
                if message.get("status") in ["complete", "stopped", "error"]:
                    break
            await asyncio.sleep(0.1) # Prevent busy-waiting
        except asyncio.CancelledError:
            break

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/start")
async def start_processing(settings: Dict[str, Any]):
    global background_process
    if background_process and background_process.is_alive():
        return {"status": "error", "message": "Processing is already running."}

    pause_event.clear()
    stop_event.clear()

    def progress_callback_wrapper(status):
        progress_queue.put(status)

    background_process = multiprocessing.Process(
        target=run_processing,
        args=(settings, progress_callback_wrapper, pause_event, stop_event)
    )
    background_process.start()
    
    # Start the task that broadcasts progress
    asyncio.create_task(progress_broadcaster())

    return {"status": "started", "message": "Processing started."}

@app.post("/pause")
async def pause_processing():
    pause_event.set()
    return {"status": "paused", "message": "Processing paused."}

@app.post("/resume")
async def resume_processing():
    pause_event.clear()
    return {"status": "resumed", "message": "Processing resumed."}

@app.post("/stop")
async def stop_processing(save: bool = False):
    stop_event.set()
    # The `run_processing` function will handle the cleanup and saving.
    # We just signal it to stop.
    return {"status": "stopping", "message": "Processing stopping..."}

if __name__ == "__main__":
    # This is for running the backend independently for development
    uvicorn.run(app, host="127.0.0.1", port=8000)
