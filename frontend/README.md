# RAG Optimization Engine UI

Ready-to-connect React/Vite frontend. Run `npm install` then `npm run dev`.

Backend integration points are already isolated in `src/main.jsx` in the `api` object. Replace the mock upload/chat handlers with your FastAPI calls.

Suggested backend endpoints: `POST /documents/upload`, `GET /documents`, `DELETE /documents/:id`, `POST /documents/:id/reindex`, `POST /ask`.

The UI supports: workspace dashboard, 5-PDF upload modal, validation, document library, processing status, multi-document selection, chat, retrieval-mode indicator, source cards, page viewer, thumbnails, and settings.
