# PregnancyAI

PregnancyAI is a FastAPI and React application for fetal brain ultrasound workflows. It combines user authentication, scan upload handling, ultrasound classification hooks, Grad-CAM style result visualization, and a pregnancy education chatbot.

## Features

- FastAPI backend with versioned API routes
- React/Vite frontend
- JWT-based authentication and role-aware access
- Upload and scan history workflow
- Optional fetal ultrasound model integration through `ml_work/` when enabled locally
- Intent-aware chatbot with OpenRouter/Gemini-compatible configuration
- Alembic database migrations
- Pytest coverage for core backend API contracts

## Repository Layout

```text
backend/          FastAPI app, database models, chatbot, ML integration, tests
frontend/         React/Vite client
ml_work/          Local notebooks and optional ML artifacts
design-previews/  Static design reference files
docs/             Project documentation
```

## What Is Not Committed

This repository intentionally excludes local secrets, dependency folders, build outputs, uploads, generated scan results, and large model artifacts. ML scan analysis is disabled by default so the app can run without model weights.

To enable ML locally, set `ENABLE_ML_ANALYSIS=true` and provide expected local ML files such as:

```text
ml_work/module_a_3class_leakage_checked.pth
ml_work/abnormal_classifier_leakage_checked.pth
```

The intent classifier can also load an optional trained model from:

```text
backend/data/intent_training/trained_model/
```

Large files such as `.pth`, `.pt`, `.bin`, and `.safetensors` are ignored.

Install optional ML dependencies only when enabling scan analysis:

```bash
cd backend
pip install -r requirements-ml.txt
```

## Backend Setup

Create a virtual environment and install dependencies:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create your local environment file:

```bash
copy .env.example .env
```

Then replace the placeholder values in `backend/.env`.

Required variables:

```env
OPENROUTER_API_KEY=your_openrouter_key
DATABASE_URL=sqlite:///./pregnancyai.db
SECRET_KEY=replace_with_a_long_random_secret
ENABLE_ML_ANALYSIS=false
ML_MODEL_VERSION=v3
```

Optional:

```env
GEMINI_API_KEY=your_gemini_key
OPENROUTER_MODEL=tngtech/deepseek-r1t2-chimera:free
```

Run database migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn backend.api.main:app --reload
```

The API will be available at `http://localhost:8000`.

## Frontend Setup

Install dependencies and start Vite:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at the URL printed by Vite, usually `http://localhost:5173`.

## Tests

Run backend tests from the repository root:

```bash
pytest backend/tests
```

Build the frontend:

```bash
cd frontend
npm run build
```

## Security Notes

- Do not commit `backend/.env` or any `.env.*` file containing real credentials.
- Do not commit model weights, generated uploads, scan results, local databases, logs, or dependency folders.
- Keep `ENABLE_ML_ANALYSIS=false` for public/demo deployments unless model artifacts are managed separately.
- Rotate any API keys that were ever committed before publishing the repository.
- Review `git status` and `git diff --cached` before pushing.

## Publishing Checklist

```bash
git status
git diff --cached
git add README.md .gitignore backend/requirements.txt backend/.env.example
git commit -m "Prepare repository for GitHub"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```
