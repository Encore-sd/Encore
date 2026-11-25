# AI

## Project Structure:

```
ai/
├── api/                # receives requests, returns responses, hands off to pipeline
├── pipeline/           # end to end pipeline using all stages
├── shared/             # shared between all models
├── transcription/      # audio transcription
├── trigger_model/      # cheap trigger + expensive fallback trigger
├── representation/
│   ├── kg/             # knowledge graph construction and updates
│   └── retriever/      # embeds the question and requests the top rows from the backend's search endpoint
├── queries/            # query handling and processing
├── evals/              # benchmarks and model quality [STRETCH]
└── tests/              # pytest tests, sample inputs in tests/fixtures/
```

--- 

### Models (Ollama):

Query answering uses Qwen3-4b and uses Ollama that `queries/answer_model.py` sends requests to.

Setup (once):
1. Install Ollama (macOS: `brew install ollama`, unsure for other OS')
2. Start the server: `ollama serve`
3. In a second terminal, download the models: 
   - `ollama pull qwen3:4b-instruct`
   - `ollama pull embeddinggemma:300m`

To run: keep `ollama serve` running in one terminal while using the pipeline.

The server address and model name are set by `OLLAMA_URL` and `ANSWER_MODEL` in `.env` (see `.env.example`). Use the `qwen3:4b-instruct` tag exactly; the plain `qwen3:4b` tag returns its reasoning instead of an answer.

--- 

### API Server (api):

Run from the `ai/` folder, with `ollama serve` already running:

`uv run --env-file .env uvicorn api.server:app`

The server listens on `http://127.0.0.1:8000`. Open `/docs` there to see and try the endpoints.

- `POST /audio`: takes an audio file, returns the transcript, keep decision and embedding.
- `POST /query`: takes a question and user ID, returns an answer.

Request and response shapes are in `contracts/ai-endpoints.md`. `/query` needs `SEARCH_URL` in `.env` to point at the backend's search endpoint.

---
