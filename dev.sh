#!/bin/bash
# Launch the web app: FastAPI backend (:8000) + Vite dark frontend (:5173).
# Open http://localhost:5173 once both are up.
cd "$(dirname "$0")"
export PATH="$PATH:/Users/shaunblaszak/Library/Python/3.11/bin"

python3 -m uvicorn api.server:app --port 8000 --reload &
BACKEND=$!
( cd web && npm run dev ) &
FRONTEND=$!

trap "kill $BACKEND $FRONTEND 2>/dev/null" EXIT INT TERM
echo "Backend :8000  ·  Frontend :5173  →  open http://localhost:5173"
wait
