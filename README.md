# Chrome Docker Security Project

This project consists of a Python backend service and a Chrome browser extension designed to interact with it, likely for security analysis purposes (e.g., URL scanning).

## Prerequisites

*   Docker: [Install Docker](https://docs.docker.com/engine/install/)
*   Python 3 (for potential local development/testing, though running via Docker is recommended)
*   Google Chrome or Chromium browser

## Structure

*   `backend/`: Contains the Python backend service (FastAPI/Uvicorn) and its Dockerfile.
*   `extension/`: Contains the Chrome browser extension source files.
*   `docker/`: Contains an additional Dockerfile (`Dockerfile.urlscanner`), its exact role needs clarification, but seems related to URL analysis using Playwright. The backend Dockerfile also includes Playwright.

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
    **(Note:** You need a `.env` file in the project root with your `GOOGLE_API_KEY` for the AI analysis feature to work.)
    ```bash
    docker run -d --name backend-service --env-file .env -p 8000:8000 chrome-security-backend uvicorn main:app --host 0.0.0.0 --port 8000
    ```
    *   `-d`: Runs the container in detached mode.
    *   `--name backend-service`: Assigns a name to the container.
    *   `--env-file .env`: Loads environment variables (like `GOOGLE_API_KEY`) from the `.env` file.
    *   `-p 8000:8000`: Maps port 8000 on your host to port 8000 in the container.
    *   `chrome-security-backend`: The name of the image built previously.
    *   `uvicorn main:app --host 0.0.0.0 --port 8000`: This is the command to start the web server inside the container.

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
2.  Create a `.env` file in the project root directory with the line: `GOOGLE_API_KEY=YOUR_API_KEY_HERE` (Replace `YOUR_API_KEY_HERE` with your actual Google AI Studio API key).
3.  Click the extension icon in your Chrome toolbar.
4.  Interact with the extension popup (`popup.html` / `popup.js`). It communicates with the backend service running at `http://localhost:8000`.

## Notes

*   The purpose and usage of `docker/Dockerfile.urlscanner` are currently unclear from the project structure alone. It might be for separate testing or part of a different workflow. The backend's Dockerfile also includes Playwright setup, suggesting scanning might occur within the main backend service.
*   The backend uses Google Gemini for AI analysis. You need to provide your own API key via a `.env` file for this feature to work.
*   Review `backend/main.py` and `extension/popup.js` / `extension/background.js` for specific API endpoints and extension behavior. 