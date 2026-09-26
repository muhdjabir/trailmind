# web

Barebones Next.js chat UI (presentation only — see [CLAUDE.md](../CLAUDE.md)).
Talks to the FastAPI service's `POST /chat`; no chat history is kept
server-side, so each message is a fresh, independent question for now.

## Setup

```
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Requires the
FastAPI service running at `http://localhost:8000` (see
`../agent/README.md`) — `docker compose up -d`, `ollama serve`, then
`uvicorn app.main:app --reload` from `agent/`.

To point at a different backend URL, set `NEXT_PUBLIC_API_URL` in a
`.env.local` file (gitignored):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```
