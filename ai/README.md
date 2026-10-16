# AI

## Project Structure:

```ai/
├── api/                # receives requests, returns responses, hands off to pipeline
├── pipeline/           # end to end pipeline using all stages
├── shared/             # shared between all models
├── transcription/      # audio transcription
├── trigger_model/      # cheap trigger + expensive fallback trigger
├── representation/
│   ├── kg/             # knowledge graph construction and updates
│   └── retriever/      # retrieval over the KG
├── queries/            # query handling and processing
├── evals/              # benchmarks and model quality [STRETCH]
└── tests/              # pytest tests; sample inputs in tests/fixtures/```
