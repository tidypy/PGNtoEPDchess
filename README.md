# PGN to EPD GUI

This is a desktop application for converting large PGN chess database files to EPD format.

## Project Setup

### Backend

1.  **Install Python Dependencies:**

    Navigate to the `backend` directory and install the required packages.

    ```bash
    cd backend
    pip install -r requirements.txt
    cd ..
    ```

### Frontend

1.  **Install Frontend Dependencies:**

    Navigate to the `frontend` directory and install the npm packages.

    ```bash
    cd frontend
    npm install
    cd ..
    ```

## Development Mode

For a smoother development experience, it is recommended to run the backend and frontend servers separately.

1.  **Run the Backend Server:**

    Open a terminal and run the Python server.

    ```bash
    python backend/server.py
    ```

2.  **Run the Frontend Server:**

    Open another terminal and run the Svelte development server.

    ```bash
    pip install -r backend/requirements.txt
    ```
    If running Arch Linux you may need to create a Venv to utilize PIP as python will be locked. Or attempt to install the dependencies through AUR.  

2.  **Install frontend dependencies:**

    ```bash
    pip install pyinstaller
    ```

2.  **Build the Backend Executable:**

    Run the following command from the root of the project to create the backend executable:

    ```bash
    pyinstaller --name=backend-server --onefile --noconsole backend/server.py
    ```

    This will create a file named `backend-server` (or `backend-server.exe` on Windows) in the `dist` directory.

3.  **Configure Tauri:**

    The `tauri.conf.json` file is already configured to use the `backend-server` executable as a sidecar. You may need to adjust the path to the executable in the `tauri.conf.json` file if you move it from the `dist` directory.

4.  **Build the Tauri Application:**

    Run the following command to build the final application:

    ```bash
    npx tauri build
    ```

This will create a standalone executable file in the `target/release/bundle` directory.
