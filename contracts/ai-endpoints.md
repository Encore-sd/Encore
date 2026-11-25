# AI service endpoints

## POST /audio (backend → AI)

Form upload, field `file`: one complete audio file (wav, mp3, m4a, ogg, flac, webm, aiff).

```json
{
  "transcript_string": "text, or \"\" if no speech",
  "start_time": 0.0,
  "end_time": 6.4,
  "keep": true,
  "confidence": 0.82,
  "reason": "label",
  "embedding": [768 numbers]
}
```

No speech: `transcript_string` is `""`, everything else is `null`. Times are seconds within the file.
TypeSafeError(s) raised during Trigger Model classification: `keep` and `confidence` are `null`, `reason` contains the exception/type of error
Errors: 415 not an audio file, 422 no `file` field, 503 embedding model unavailable (keep the file and send it again later).

## POST /query (backend → AI)

```json
{ "question": "where is my locker", "userID": 7 }
```
```json
{ "answer": "text, or \"I don't have a memory of that.\"" }
```

Errors: 422 bad body, 500 search or answer model unavailable.

## POST /retriever (AI → backend)

```json
{ "userID": 7, "topK": 10, "embedding": [768 numbers], "question": "text, unused for now" }
```

Returns a bare JSON array of up to `topK` rows for that user, closest first by cosine distance:

```json
[
  {
    "id": 183,
    "transcript_string": "text",
    "start_time": 0.0,
    "end_time": 6.4,
    "captured_at": "2026-11-17T14:36:00-05:00",
    "distance": 0.24
  }
]
```

Fewer rows than `topK`: return what exists. No rows: `[]` with status 200.
`transcript_string` must keep that exact name. `captured_at` is a placeholder name.
