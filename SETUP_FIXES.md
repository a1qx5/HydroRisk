# HydroRisk — Setup & Fixes Guide

This document explains every change made to get real data flowing through the pipeline.
All fixes have been committed and pushed to `master`.

---

## 1. Environment — `.env` (repo root)

The `.env` file must exist at `c:\HydroRisk\.env` with these values:

```env
SENTINEL_HUB_CLIENT_ID="sh-e82a5674-7ea6-46e3-aa38-26d16fa22108"
SENTINEL_HUB_CLIENT_SECRET="VLRXH1Hoq9SOdPh6mHPvg95C8jHhQVcT"
OPENTOPOGRAPHY_API_KEY="67d58505662fa39096b7015ae7a5d66c"
```

> ⚠️ This file is git-ignored. Anyone cloning the repo must create it manually.

---

## 2. `backend/config.py` — Force `.env` override

**Problem:** If `OPENTOPOGRAPHY_API_KEY` was already set in the system environment
from a previous session, `load_dotenv()` would silently keep the old (invalid) value.

**Fix:** Added `override=True` so `.env` always wins.

```python
# Before
load_dotenv(find_dotenv())

# After
load_dotenv(find_dotenv(), override=True)
```

---

## 3. `backend/layer1/terrain.py` — Fix broken import

**Problem:** `from backend.config import ...` crashes because the server runs from
inside the `backend/` directory, so there is no parent package called `backend`.

**Fix:** Use a local relative import instead.

```python
# Before (line 17)
from backend.config import OPENTOPOGRAPHY_API_KEY

# After
from config import OPENTOPOGRAPHY_API_KEY
```

---

## 4. `backend/layer1/flood_history.py` — Two fixes

### Fix A — Broken import (same root cause as terrain.py)

```python
# Before (inside get_flood_history)
from backend.config import SENTINEL_HUB_CLIENT_ID, SENTINEL_HUB_CLIENT_SECRET

# After
from config import SENTINEL_HUB_CLIENT_ID, SENTINEL_HUB_CLIENT_SECRET
```

### Fix B — 15-second socket timeout

**Problem:** `config.download_timeout_seconds = 90` is set correctly, but it does not
reach the underlying urllib3 socket layer. The OS default socket read timeout of
~15 seconds fires first, causing every Sentinel-1 year query to fail silently and
return `False, False` — making flood history always appear as "NONE".

**Fix:** Override the socket default explicitly at the start of `get_flood_history()`.

```python
# Added at top of file
import socket

# Added as first line of get_flood_history()
socket.setdefaulttimeout(90)
```

> **Note:** This means each analysis call may take 1–2 minutes while the 12-year
> Sentinel-1 archive is queried. This is expected behaviour, not a hang.

---

## 5. Running the backend

Always run from inside the `backend/` directory:

```bash
cd c:\HydroRisk\backend
python api.py
```

Do **not** run as `python -m backend.api` from the repo root — the import paths
are written for the `backend/` working directory.

---

## 6. Running the frontend

```bash
cd c:\HydroRisk\frontend
python -m http.server 8000
```

Then open: `http://localhost:8000`

---

## 7. Google Maps Street View (frontend)

The **360° Street View** button uses the Google Maps JavaScript API.
The key is already embedded in `frontend/index.html`:

```
AIzaSyA7sqKfh5JTgUCLA5-S6klPygIwx0T8Tyw
```

If the key ever expires or hits quota, replace it in the `<script>` tag in `index.html`.
The key requires **Maps JavaScript API** and **Street View Static API** to be enabled
in Google Cloud Console.
