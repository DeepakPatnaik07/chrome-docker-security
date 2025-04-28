# chrome-docker-security

# Chrome Docker Security Project

This project consists of a Python backend service and a Chrome browser extension designed to interact with it, likely for security analysis purposes (e.g., URL scanning).

## Prerequisites

*   Docker: [Install Docker](https://docs.docker.com/engine/install/)
*   Python 3 (for potential local development/testing, though running via Docker is recommended)
*   Google Chrome or Chromium browser

## Structure

*   `backend/`: Contains the Python backend service (FastAPI/Uvicorn suspected) and its Dockerfile.
*   `extension/`: Contains the Chrome browser extension source files.
*   `docker/`: Contains an additional Dockerfile (`Dockerfile.urlscanner`), its exact role needs clarification, but seems related to URL analysis using Playwright.

## Setup and Running

### 1. Backend Service

The backend service runs inside a Docker container.

*   **Build the backend Docker image:**
    Navigate to the `backend` directory and run:
    ```bash
    cd backend
    docker build -t chrome-security-backend .
    cd ..
    ```

*   **Run the backend container:**
    ```bash
    docker run -d --name backend-service -p 8000:8000 chrome-security-backend uvicorn main:app --host 0.0.0.0 --port 8000
    ```
    *   `-d`: Runs the container in detached mode.
    *   `--name backend-service`: Assigns a name to the container.
    *   `-p 8000:8000`: Maps port 8000 on your host to port 8000 in the container.
    *   `chrome-security-backend`: The name of the image built previously.
    *   `uvicorn main:app --host 0.0.0.0 --port 8000`: This is the command to start the web server inside the container (overriding the commented-out CMD in the Dockerfile).

    You can check the container logs using:
    ```bash
    docker logs backend-service
    ```

### 2. Chrome Extension

*   Open Chrome/Chromium.
*   Go to `chrome://extensions/`.
*   Enable "Developer mode" (usually a toggle in the top right).
*   Click "Load unpacked".
*   Select the `extension` directory from this project.
*   The extension icon should appear in your browser toolbar.

## Usage

1.  Ensure the backend service container is running.
2.  Click the extension icon in your Chrome toolbar.
3.  Interact with the extension popup (`popup.html` / `popup.js`). It likely communicates with the backend service running at `http://localhost:8000`. (The exact functionality depends on the implementation in `popup.js` and `background.js`).

## Notes

*   The purpose and usage of `docker/Dockerfile.urlscanner` are currently unclear from the project structure alone. It might be for separate testing or part of a different workflow. The backend's Dockerfile also includes Playwright setup, suggesting scanning might occur within the main backend service.
*   Review `backend/main.py` and `extension/popup.js` / `extension/background.js` for specific API endpoints and extension behavior.
