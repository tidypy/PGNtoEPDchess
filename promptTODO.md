# **Generative Prompt: Svelte and Python GUI for PGN Processor**

## **Project Overview**

You are an expert full-stack developer. Your task is to create a local desktop application that provides a user-friendly graphical interface (GUI) for an existing, powerful Python script. The script (epdpgnPython.py) is a command-line tool that processes very large chess PGN database files to extract EPD positions.

The final product will be a self-contained desktop application that is **cross-platform (Windows and Linux)**. The user will interact with a modern Svelte frontend, which will communicate with a Python backend that runs the processing logic.

## **Core Technical Challenge**

The Python script is a CPU-intensive, long-running task that uses multiprocessing and can take hours to complete on large files. The single most important requirement is that the **GUI must never freeze**. The user must receive **real-time progress updates** and have **full control over the process (pause, resume, stop)**.

## **Technology Stack**

* **Frontend:** **Svelte**.  
* **Backend:** **Python**. **FastAPI** is the preferred web server framework for its modern async capabilities.  
* **Real-time Communication:** Use **WebSockets** for pushing progress and status updates from the Python backend to the Svelte frontend. This is a mandatory requirement.  
* **Packaging:** The entire application should be wrapped into a single, executable desktop application. **Use Tauri** for this, as it produces efficient, cross-platform binaries for Windows and Linux. Provide all necessary configuration files.

## **Backend (Python API) Requirements**

1. **Refactor the Script:** Convert the existing command-line script into a Python module. The core logic inside the main() function should be refactored into a callable function (e.g., run\_processing(settings, progress\_callback, pause\_event, stop\_event)).  
2. **Implement Process Control Logic:**  
   * The backend must manage the state of the task (e.g., RUNNING, PAUSED, STOPPING).  
   * **Pause/Resume:** Use a multiprocessing.Event to signal a pause. The worker processes must check this event periodically and wait if it's set.  
   * **Stop/Cancel:** Use another multiprocessing.Event to signal a stop. When triggered, the workers should terminate gracefully.  
3. **Modify for Progress Reporting:** This new function must not print to the console or use tqdm. Instead, it should accept a progress\_callback function. As it completes tasks, it should call this callback with progress information (e.g., progress\_callback({"status": "processing", "progress": 55, "message": "Processed chunk 5/10"})).  
4. **Create the API:**  
   * Create a main API file (e.g., server.py).  
   * /start\_processing: A POST endpoint that is **non-blocking**. It starts the run\_processing function in a separate background process.  
   * /pause\_processing: An endpoint that sets the pause event.  
   * /resume\_processing: An endpoint that clears the pause event.  
   * /stop\_processing: An endpoint that sets the stop event. It should accept a query parameter (e.g., ?save=true) to determine its behavior.  
     * If save=true, the backend should stop the workers, then proceed to merge the existing temporary files and save the partial EPD result.  
     * If save=false, the backend should stop the workers and immediately delete all temporary files.  
   * Implement a WebSocket endpoint (e.g., /ws). The Svelte frontend will connect to this.  
5. **WebSocket Logic:**  
   * The progress\_callback should push JSON status messages to all connected WebSocket clients.  
   * Messages must include the current state (running, paused, stopped, complete), progress percentage, a message, and an is\_complete flag. Also, handle and report any errors.

## **Frontend (Svelte UI) Requirements**

1. **UI Design:** A clean, modern, single-page interface. The layout should be intuitive.  
2. **Input Controls:**  
   * **Input File:** A file dialog button for .pgn files.  
   * **Output EPD File:** A file save dialog button.  
   * **Min/Max Ply, Min ELO, ECO Prefix, Workers:** Appropriate input fields.  
3. **Action & Feedback Controls:**  
   * A **"Start Processing"** button, disabled while a task is running.  
   * A **"Pause" / "Resume"** button that toggles based on the current state. Only visible during processing.  
   * A **"Stop"** button. When clicked, it should present a confirmation dialog asking the user if they want to "Save Partial Results" or "Discard Results". This will determine the save parameter for the API call.  
   * A large, clear **Progress Bar** that updates in real-time.  
   * A **Log Panel** that displays status messages from the backend.  
4. **WebSocket Client:**  
   * The app must connect to the WebSocket on startup.  
   * It must listen for incoming messages and dynamically update the state of all UI elements (buttons, progress bar, logs).

## **TO-DO List for AI Generation**

Here is the step-by-step plan to generate the complete application. Please follow it in order.

1. **Set** up Project Structure: Create a root directory with two subdirectories: /frontend and /backend.  
2. **Refactor** Backend Logic: Create /backend/processor.py. Refactor the core logic into a callable function.  
3. **Implement** Process Control in Backend: Integrate multiprocessing.Event for pause/resume and stop functionality into the processor.py worker loops.  
4. **Build** Backend API: Create /backend/server.py. Implement the FastAPI server, all required endpoints (/start, /pause, /resume, /stop), and the /ws WebSocket endpoint.  
5. **Create** Svelte Project: Initialize a new Svelte project in the /frontend directory.  
6. **Build** Svelte UI Components: Create Svelte components for all inputs, buttons (including state-driven Pause/Resume/Stop), the progress bar, and the log panel.  
7. **Implement** Svelte Logic: Write the Svelte code to handle user input, manage UI state based on WebSocket messages, and make API calls to the control endpoints.  
8. **Configure** Tauri Packaging: Add the necessary tauri.conf.json and other configuration files to the root directory. The configuration must properly start the Python backend server as a "sidecar" and load the Svelte frontend for both Windows and Linux builds.  
9. **Create** Documentation: Generate a README.md file in the root directory that explains the project and provides clear, step-by-step instructions on how to install dependencies (requirements.txt, package.json) and how to build and run the final packaged application on both Windows and Linux.

## **Refinement and Bug Fix TODOs**

*   Refactor the main `run_processing` function into smaller, more focused helper functions to improve code clarity and maintainability.
*   ~~Add server-side validation for the settings received from the frontend to prevent errors from invalid input like bad file paths.~~ (Implemented)
*   ~~Expand the unit test suite to cover the core filtering logic in `_is_game_filtered_out` to ensure its reliability.~~ (Implemented)
*   ~~Improve error reporting from worker processes back to the main process and frontend.~~ (Implemented)
*   **Stabilize Development Environment:** The `uvicorn --reload` flag was found to be unstable with Python's `multiprocessing` library, causing silent backend crashes. The development script (`start_dev.sh`) has been modified to run the server in a stable mode without hot-reloading to guarantee a working backend. (Implemented)
*   **Fix Worker Process Creation:** Refactored the `multiprocessing.Pool` in `processor.py` to use an `initializer` function. This resolves silent crashes caused by issues with passing shared `Event` objects to worker processes. (Implemented)
*   **Improve Stop/Cancel UI:** Replaced the native browser `confirm()` dialog with a custom, non-blocking modal in the Svelte UI for a better user experience when stopping a process. (Implemented)
*   **Add Defensive Error Handling:** Added robust `try...except` blocks to critical backend paths (like the `/start` endpoint) to ensure any errors are logged and reported to the UI instead of causing silent failures. (Implemented)