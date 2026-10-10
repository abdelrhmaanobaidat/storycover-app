# storycover-app

Application code for **StoryCover**: upload a photo + a story name, and a Gemini
image-capable model generates a story-book cover, which is stored in a locked-down GCS
bucket and returned to the user.

## Layout
```
storycover-app/
├── src/storycover/
│   ├── main.py               # FastAPI: / (upload UI), POST /api/generate, /healthz, /metrics
│   ├── gemini.py             # calls Gemini with the uploaded image + title
│   ├── storage.py            # GCS upload + v4 signed URL via Workload Identity
│   └── config.py             # settings; reads GEMINI_API_KEY from env (VSO-synced)
├── tests/                    # unit tests, Gemini/GCS mocked
├── Dockerfile                # multi-stage, non-root, read-only-rootfs friendly
├── pyproject.toml            # deps + pytest config
└── .github/workflows/ci.yaml # test → build → Trivy scan → push → bump config overlay
```

## How the secret reaches the app (no secret in Git/image)
Vault holds the Gemini key. Argo CD applies a `VaultStaticSecret` CR; the **Vault Secrets
Operator** materialises it as a Kubernetes Secret, which the Deployment exposes to the app
as `GEMINI_API_KEY`. `config.py` reads that env var — the repo contains no key, only the
reference.

## CI
On merge to `main`: run tests, build the image, scan it with Trivy (fails on HIGH/CRITICAL),
push to Artifact Registry tagged with the immutable git SHA, then bump that tag in
`storycover-config/overlays/dev`. GCP auth is keyless via Workload Identity Federation
(`app-ci@storycover-dev`). The only secret the pipeline needs is `CONFIG_REPO_TOKEN` — a
fine-grained PAT with write access to `storycover-config` for the cross-repo bump.

## Local development
```
python3.12 -m venv .venv && . .venv/bin/activate
pip install .[dev]
pytest
uvicorn storycover.main:app --reload   # needs GEMINI_API_KEY and GCS_BUCKET to generate
```
