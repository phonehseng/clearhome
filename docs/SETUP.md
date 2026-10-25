# Setup and troubleshooting

## Requirements

Use Python 3.12, Git, a browser, and internet access to install dependencies. Python 3.9 appears in older setup notes; use a maintained Python installation for new environments. No npm install, frontend compilation, SQL server, or Gemini key is required to browse the catalog.

## First installation: macOS or Linux

Run from the directory where you keep projects:

```bash
git clone https://github.com/phonehseng/clearhome.git
cd clearhome
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python backend/app.py
```

Open `http://localhost:8000`. The terminal must keep running. Stop the development server with **Ctrl+C**. If the repo is already cloned, enter its directory and run `git pull` instead of cloning again.

The virtual environment provides the `python` command after activation. Before activation, macOS commonly provides only `python3`.

## First installation: Windows PowerShell

```powershell
git clone https://github.com/phonehseng/clearhome.git
cd clearhome
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python backend/app.py
```

If PowerShell prevents activation, run the virtual environment directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe backend/app.py
```

## Later sessions

```bash
git pull
source .venv/bin/activate
python backend/app.py
```

Run `python -m pip install -r backend/requirements.txt` again when requirements change or dependencies are missing. Restart the backend after pulling backend changes, then reload the browser. Pulling code alone does not start a localhost server. A server running on someone else's computer is not your localhost.

For another local port without the debug reloader:

```bash
python -m flask --app backend/app run --host 127.0.0.1 --port 8001 --no-reload
```

Open `http://localhost:8001`. Browser-key referrer restrictions must include that port when testing Google Maps.

## Optional configuration

Copy the placeholder file only if you want integrations:

```bash
cp .env.example .env
```

Edit `.env` locally. `backend/matcher.py` loads it through `python-dotenv`. Existing process environment values take precedence over dotenv's default loading. Restart the server after changes. Never paste credentials into chat, commit `.env`, or expose server credentials to the frontend.

| Setting | Purpose | Default / requirement |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API access for Gemma answers and grounded discovery | Optional for catalog browsing; required for Gemini-backed calls |
| `GOOGLE_MAPS_SERVER_API_KEY` | Backend Places and Routes requests | Optional; walking searches report configuration guidance without it |
| `GOOGLE_MAPS_BROWSER_API_KEY` | Maps JavaScript rendering | Optional; returned intentionally by `/api/maps-config`, so restrict it to allowed websites and APIs |
| `GEMMA_GPU_URL` | Private Ollama-compatible Gemma service | Optional; absent means use Gemini where needed |
| `GEMMA_GPU_MODEL` | GPU model name | `gemma4:26b`; read when `gemma_gpu.py` imports |
| `GEMMA_GPU_TOKEN` | Local identity token for private GPU access | Optional local testing; Cloud Run uses its service identity when absent |
| `CLEARHOME_READ_ONLY` | Disable HTTP review writes and automatic local queue/freshness writes | Set exactly `1` for hosted copies; does not disable standalone maintenance scripts |
| `WARM_EXAMPLES` | Precompute example answers at module startup | Set exactly `1` to enable; may call AI services |
| `INCLUDE_UNVERIFIED` | Legacy matcher testing switch | Leave unset for normal use; not a way to approve resources for publication |
| `PORT` | Gunicorn container bind port | Supplied by Cloud Run; `python backend/app.py` uses port 8000 instead |

The checked-in `.env.example` lists the three basic API keys; advanced settings above are optional and need not be added for local browsing. The Gemini model identifier in `backend/matcher.py` is `gemma-4-26b-a4b-it`. Successful access depends on the provider, project, model availability, quota, and account permissions.

For Google API enablement, key restrictions, and billing setup, use [WALKABILITY.md](../WALKABILITY.md). For Secret Manager and Cloud Run configuration, use [DEPLOY.md](../DEPLOY.md). For private GPU setup, use [gemma/README.md](../gemma/README.md). These integrations are not needed for the basic UI.

## Troubleshooting

| Symptom | Check / action |
|---|---|
| `zsh: command not found: python` | Create the environment with `python3`, activate it, then use `python`. |
| `ModuleNotFoundError` | Activate `.venv` and install the current requirements with that interpreter. Use `python -m pip`, not an unrelated global pip. |
| Old traceback importing NumPy or OCR | Confirm `git branch --show-current` is `main`, pull, and restart. The current app has no lease/OCR upload path and does not require NumPy. |
| Browser cannot reach localhost | Start the backend, check its terminal for errors, and use the exact printed host and port. |
| Port 8000 already in use | Stop the previous process or use the Flask port-8001 command above. |
| Pretty-printed JSON instead of cards | Open `/app#listings`; `/api/listings` is intentionally raw JSON. |
| Chat cannot answer | Catalog browsing still works. Check optional AI configuration and quota; never post the key when reporting an error. |
| Map unavailable | Check browser/server keys, enabled services, website restrictions, internet access, and browser console errors. Results and official links may remain useful. |
| Photos do not load | Check provider access and the image source. Try the image audit on a network that can reach the publisher; do not substitute another building. |
| Few or no listings | Relax filters; budget filters exclude unknown rents. Closed, stale, invalid, hidden, and unverified records may be excluded. |
| Review save returns 403 | Saves require loopback access and `CLEARHOME_READ_ONLY` unset. Hosted review pages are read-only. |
| Changes do not appear | Confirm the branch, restart the backend, and hard-refresh. A Git push is separate from a successful production deployment. |

The built-in Flask server runs with debug enabled when started as `python backend/app.py`. Keep it for local development; the production container uses Gunicorn.
