import asyncio
import multiprocessing
from typing import Dict, Any, List
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field

from .processor import run_processing

logging.basicConfig(level=logging.INFO)

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

# Define a Pydantic model to handle settings from the frontend.
# This robustly handles the camelCase from JS to snake_case in Python.
class ProcessingSettings(BaseModel):
    input_file: str = Field(alias='inputFile')
    output_file: str = Field(alias='outputFile')
    min_elo: int = Field(alias='minElo')
    max_ply: int = Field(alias='maxPly')
    eco_prefix: str = Field(alias='ecoPrefix')
    workers: int

    class Config:
        allow_population_by_field_name = True

# --- State Management ---
# These will be initialized on startup to avoid issues with uvicorn's reloader.
process_manager = None
pause_event = None
stop_event = None
stop_save_flag = None
progress_queue = None

async def progress_broadcaster():
    """A single, long-running task to get messages from the queue and broadcast them."""
    while True:
        try:
            if not progress_queue.empty():
                message = progress_queue.get_nowait()
                await manager.broadcast(message)
            await asyncio.sleep(0.1)  # Prevent busy-waiting
        except asyncio.CancelledError:
            logging.info("Progress broadcaster task cancelled.")
            break
        except Exception as e:
            logging.error(f"Error in progress broadcaster: {e}")
            await asyncio.sleep(1) # Avoid fast-spinning on error

@app.on_event("startup")
async def on_startup():
    """Start the broadcaster task and initialize multiprocessing resources."""
    global process_manager, pause_event, stop_event, stop_save_flag, progress_queue

    # Initialize shared objects here to ensure they are created in the main
    # event loop of the running server, not in the reloader process.
    # This is crucial for stability with `uvicorn --reload`.
    if process_manager is None:
        logging.info("Initializing multiprocessing manager and shared objects...")
        process_manager = multiprocessing.Manager()
        pause_event = process_manager.Event()
        stop_event = process_manager.Event()
        stop_save_flag = process_manager.Value('b', 0)
        progress_queue = process_manager.Queue()

    app.state.broadcaster_task = asyncio.create_task(progress_broadcaster())
    app.state.background_process = None

@app.on_event("shutdown")
async def on_shutdown():
    """Cleanly stop the broadcaster task when the server shuts down."""
    app.state.broadcaster_task.cancel()
    try:
        await app.state.broadcaster_task
    except asyncio.CancelledError:
        pass # This is expected

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/status")
async def get_status():
    """Endpoint for the frontend to check the current status."""
    if hasattr(app.state, 'background_process') and app.state.background_process and app.state.background_process.is_alive():
        status = "paused" if pause_event.is_set() else "processing"
        return {"status": status, "message": "A process is currently running."}
    return {"status": "idle", "message": "No process is running."}

@app.post("/start")
async def start_processing(settings: ProcessingSettings):
    try:
        if hasattr(app.state, 'background_process') and app.state.background_process and app.state.background_process.is_alive():
            return {"status": "error", "message": "Processing is already running."}

        # Clear any stale messages from a previous run
        while not progress_queue.empty():
            progress_queue.get_nowait()

        # Reset events for the new run
        pause_event.clear()
        stop_event.clear()
        stop_save_flag.value = 0  # Reset on new run

        def progress_callback_wrapper(status):
            """This function is called from the background process to send updates."""
            progress_queue.put(status)

        logging.info("Preparing to start background process...")
        # Convert the Pydantic model to a dictionary with Python-style snake_case keys
        settings_dict = settings.dict()

        # Create and start the new background process
        app.state.background_process = multiprocessing.Process(
            target=run_processing,
            args=(settings_dict, progress_callback_wrapper, pause_event, stop_event, stop_save_flag),
        )
        app.state.background_process.start()
        logging.info(f"Background process started with PID: {app.state.background_process.pid}")
        
        return {"status": "started", "message": "Processing started."}
    except Exception as e:
        logging.error(f"CRITICAL ERROR in /start endpoint: {e}", exc_info=True)
        # Also send a clear error message back to the frontend
        progress_queue.put({"status": "error", "message": f"Failed to start process: {e}", "is_complete": True})
        return {"status": "error", "message": f"Failed to start process: {e}"}

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
    if save:
        stop_save_flag.value = 1
        message = "Stopping and saving partial results..."
    else:
        stop_save_flag.value = 0
        message = "Stopping and discarding results..."

    stop_event.set()
    return {"status": "stopping", "message": message}

if __name__ == "__main__":
    # This is for running the backend independently for development
    uvicorn.run(app, host="127.0.0.1", port=8000)
