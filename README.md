# PGN to EPD GUI

This is a desktop application for converting large PGN chess database files to EPD format.

## Development

To run the application in development mode, you need to have Node.js, npm, and Python installed.

1.  **Install Python dependencies:**

    ```bash
    pip install -r backend/requirements.txt
    ```
    If running Arch Linux you may need to create a Venv to utilize PIP as python will be locked. Or attempt to install the dependencies through AUR.  

2.  **Install frontend dependencies:**

    ```bash
    npm install --prefix frontend
    ```

3.  **Run the application:**

    This will start the Svelte frontend and the Python backend server as a sidecar.

    ```bash
    npx tauri dev
    ```

## Building

To build the application for production, run the following command:

```bash
npx tauri build
```

This will create a standalone executable file in the `target/release/bundle` directory.
