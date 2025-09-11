# PGN to EPD GUI

This is a cross-platform (Windows, Linux) desktop application for converting large PGN chess database files to EPD format. It features a modern Svelte frontend and a powerful Python backend, wrapped in a Tauri container.

The application is designed to handle long-running, CPU-intensive processing without freezing the UI, providing real-time progress updates and full user control (pause, resume, stop).

## Technology Stack

*   **Frontend:** Svelte with SvelteKit
*   **Backend:** Python with FastAPI
*   **Real-time Communication:** WebSockets
*   **Desktop App Framework:** Tauri
*   **Python Packaging:** PyInstaller

---

## Project Setup

Before you can run the application in development mode or build it for production, you need to install the dependencies for both the frontend and the backend.

### 1. Backend Dependencies (Python)

Navigate to the `backend` directory and install the required packages using `pip`. It is highly recommended to use a virtual environment.

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt

# Return to the root directory
cd ..
```

### 2. Frontend Dependencies (Node.js)

Navigate to the `frontend` directory and install the required packages using `npm`.

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Return to the root directory
cd ..
```

---

## Development Mode

For a smoother development experience, you can run the backend and frontend servers separately. This allows for features like hot-reloading on the frontend.

### 1. Run the Backend Server

Open a terminal in the project's root directory and run the Python FastAPI server.

```bash
# Make sure your virtual environment is activated
python backend/server.py
```

The backend API will be available at `http://127.0.0.1:8000`.

### 2. Run the Frontend Dev Server

Open a *second* terminal in the project's root directory and run the SvelteKit development server.

```bash
# Navigate to the frontend directory
cd frontend

# Start the dev server
npm run dev
```

You can now open your browser to `http://localhost:5173` to see and interact with the application.

---

## Building for Production

To create a single, standalone desktop application, follow these steps. The process involves first building the Python backend into an executable, then building the Tauri application which bundles everything together.

### 1. Install PyInstaller

`PyInstaller` is used to package the Python server into a single executable file. If you haven't already, install it in your virtual environment.

```bash
pip install pyinstaller
```

### 2. Build the Backend Executable

From the **root of the project**, run the following command to create the backend executable.

```bash
pyinstaller --name=backend-server --onefile --noconsole backend/server.py
```

This command will create a `dist/` directory containing the `backend-server` executable (`backend-server.exe` on Windows).

### 3. Build the Tauri Application

Finally, with the backend executable in place, you can build the complete Tauri application.

```bash
# Run the Tauri build command from the root directory
npx tauri build
```

This will create the final, distributable application in the `target/release/bundle/` directory. You can find the installer or standalone executable there.
