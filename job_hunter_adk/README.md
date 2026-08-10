# Job Hunter ADK

An autonomous job application agent built using the Google ADK.

## Setup

Create a `.env` file in the root of the project with the following variables:

- `GOOGLE_API_KEY`: Your plain Gemini API key.
- `GOOGLE_GENAI_USE_VERTEXAI`: Set to `FALSE` to ensure we use the plain API key instead of Vertex.
- `OLLAMA_API_KEY`: Your Ollama Cloud API key for fallback.
- `OLLAMA_CLOUD_MODEL`: The model name for your Ollama Cloud fallback (e.g. `gpt-oss:120b-cloud`).
- `API_KEY`: Your secret API key to protect the FastAPI endpoints (used for the `X-API-Key` header).
- `DATABASE_URL`: Connection string for the SQLite database (e.g. `sqlite:///./job_hunter.db`).

## Running the API Layer

First, activate your virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then, start the FastAPI HTTP service layer (with persistent sessions) and the static HTML frontend:

```bash
uvicorn api.main:app --reload --port 8000
```

Once running, visit `http://localhost:8000/index.html` in your browser.
