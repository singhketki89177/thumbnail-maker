# Thumbnail Maker

Generate YouTube thumbnails (3 styles) from a prompt + your headshot, using
OpenAI image generation + ImageKit for hosting/transformations.

## ⚠️ Before you do anything: rotate your OpenAI key

The `.env` that was in this project had a real, working OpenAI key in it.
If that key was ever shared/uploaded anywhere outside your machine, **revoke
it now** at https://platform.openai.com/api-keys and generate a new one.
Never commit `.env` to git — `.gitignore` is already set up to block it.

## Setup

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in your real keys
uvicorn main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env            # default already points at localhost:8000
npm run dev
```

Frontend runs at `http://localhost:5173`.

## What was fixed

**Backend**
- `routes.py` / `routes_fixed.py` consolidated into one working `routes.py`
  (the SSE stream endpoint was nested inside another function, imported a
  module that didn't exist, and the job `id` type didn't match the model).
- `config.py` read `IMAGEKIT_PRIVATE_KEY` from env but `.env` defined
  `IMAGE_PRIVATE_KEY` — renamed to match.
- `imagekit_service.py`: ImageKit client wasn't given `url_endpoint`; the
  `upload()` call passed raw bytes instead of the `(filename, bytes,
  content_type)` tuple the SDK expects.
- `openai_service.py`: missing `await` on an async client call, wrong content
  key (`url` → `image_url`), and an invalid `model` field nested inside the
  `image_generation` tool definition.
- `generator.py`: DB objects were being read after their session closed
  (causes `DetachedInstanceError`); fixed by capturing needed values while
  the session is still open.
- `main.py`: removed a stray/broken import, cleaned up startup.
- Added missing `__init__.py` files so `backend` imports as a package.

**Frontend**
- `JobPage.tsx`: fixed a TypeScript strict-mode error (implicit `any` on a
  `.find()` callback parameter).

Project now type-checks cleanly (`tsc --noEmit`) and the backend imports
without errors.

## Pushing to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

`.gitignore` already excludes `venv/`, `node_modules/`, `.env`, and the
SQLite database, so secrets and build artifacts won't be pushed.
