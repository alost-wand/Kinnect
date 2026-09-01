# 🏠 KINNECT — Family Connectivity Platform

> Hackathon MVP · FastAPI + Streamlit · MySQL · AES-256 · YOLOv8 + EasyOCR · AI Health Intelligence

---

## Project Structure

```
kinnect/
├── main.py                     ← Root FastAPI app entry point (dual wrapper)
├── yolov8n.pt                  ← Pre-trained YOLOv8 model weights
├── backend/
│   ├── main.py                 ← FastAPI app configuration & router mounting
│   ├── config.py               ← Pydantic settings (reads .env)
│   ├── database.py             ← Async MySQL connection pool (aiomysql)
│   ├── models/
│   │   └── schemas.py          ← Pydantic request/response models
│   ├── routers/
│   │   ├── auth.py             ← Module 1: Auth, Workspace, & Invitations
│   │   ├── timeline.py         ← Module 2: Shared Timeline & WebSockets
│   │   ├── wearable.py         ← Module 3: Health Intelligence & AI Reports
│   │   ├── emergency.py        ← Feature 3: SOS Emergency (with Map & Siren)
│   │   ├── vault.py            ← Feature 4: Secure Vault (AES-256-CBC)
│   │   └── privacy.py          ← Feature 5: AI Privacy Shield
│   └── utils/
│       ├── auth.py             ← Password hashing (bcrypt) & JWT helpers
│       └── ws_manager.py       ← WebSocket connection & broadcast manager
├── frontend/
│   ├── app.py                  ← Streamlit root entry point & navigation hub
│   ├── api_client.py           ← HTTP wrapper for requests
│   └── pages/
│       ├── login_page.py       ← Authentication page
│       ├── workspace_page.py   ← Workspace creation & pending invites
│       ├── timeline_page.py    ← Events & chore completion
│       ├── health_page.py      ← Health overview, Sparklines, & AI Reports
│       ├── emergency_page.py   ← Map, Live GPS trigger, and siren
│       ├── vault_page.py       ← File management (Download, Upload, Delete)
│       └── privacy_page.py     ← EXIF stripping & pixelation tool
├── ai_privacy/
│   └── pipeline.py             ← 4-stage privacy pipeline (EXIF + YOLO + OCR + Haar Cascade + Noise)
├── database/
│   └── schema.sql              ← MySQL database creation & schema script
├── vault_storage/              ← Encrypted documents folder (.enc files)
├── tests/
│   ├── test_privacy.py         ← Backend API unit tests
│   └── __init__.py
├── requirements.txt            ← Python package dependencies
└── .env.example                ← Template configuration file
```

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | 3.11/3.12 recommended |
| MySQL | 8.0+ | Or MariaDB 10.6+ |
| pip | latest | `pip install --upgrade pip` |
| libheif | optional | Only needed for HEIC image support |

---

## Step-by-Step Setup

### 1. Clone / copy the project

```bash
# Navigate to the project root directory
cd kinnect
```

### 2. Create a Python virtual environment

```bash
python -m venv venv

# Activate:
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> [!NOTE]
> **PyTorch build:** The default `requirements.txt` installs a CPU-only PyTorch package. If you have a CUDA-compatible GPU, replace it with the appropriate build from [PyTorch Local Setup Guide](https://pytorch.org/get-started/locally/).

---

### 4. Set up MySQL

#### Option A — Local MySQL

```bash
# Ubuntu/Debian
sudo apt install mysql-server
sudo mysql_secure_installation

# macOS (Homebrew)
brew install mysql
brew services start mysql
```

#### Option B — Cloud MySQL

You can use cloud databases such as Railway, PlanetScale, Aiven, or Clever Cloud.

#### Create the database and user

```sql
-- Run in MySQL shell: mysql -u root -p
CREATE DATABASE kinnect_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'kinnect_user'@'localhost' IDENTIFIED BY 'kdbR85';
GRANT ALL PRIVILEGES ON kinnect_db.* TO 'kinnect_user'@'localhost';
FLUSH PRIVILEGES;
```

#### Apply the schema

```bash
mysql -u kinnect_user -pKdbR85 kinnect_db < database/schema.sql
```

---

### 5. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and configure the connection details:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=kinnect_user
DB_PASSWORD=kdbR85
DB_NAME=kinnect_db

SECRET_KEY=generate_a_64_char_random_string_here
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### 6. Run the FastAPI backend

From the `kinnect/` root directory, execute either of the following commands:

```bash
# Run using the root main.py wrapper
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or run using the backend folder module path
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it is running:
- **Root Status:** `http://localhost:8000` → `{"status": "KINNECT backend online ✅"}`
- **Interactive docs:** `http://localhost:8000/docs` → Swagger UI

---

### 7. Run the Streamlit frontend

Open a **second terminal** with the virtual environment activated, then run:

```bash
streamlit run frontend/app.py --server.port 8501
```

Access the UI at `http://localhost:8501`.

---

## Module Guide

### Module 1 — Auth & Workspace
1. **Register:** Create a personal user account.
2. **Workspace:** Initialize a unique Family Workspace (generates a random UUID).
3. **Invitation:** Invite family members by entering their username.
4. **Acception:** Invited users can log in, view pending invites in their workspace dashboard, and accept to join.

---

### Module 2 — Shared Timeline
- **Event Types:** Supports Milestones (purple), Appointments (teal), and Chores (emerald).
- **Visibility Levels:** Configure events as `public` (shared with family), `private` (visible only to the creator), or `busy_only` (hides details from others).
- **Chores:** Mark chores as complete (`✅ Done`).
- **Real-Time Sync:** WebSockets push event creation, updates, and deletion events immediately to all connected family members.

---

### Module 3 — Health Intelligence Dashboard
- **Telemetry Ingestion:** Tab `Ingest Data` enables manual simulated biometric inputs (`user_id`, `heart_rate`, `step_count`, `sleep_minutes`, `hydration_ml`, `screen_minutes`, and `recorded_date`).
- **Lifestyle Score:** Computes a custom score (0–100) based on weighted biometric parameters (sleep, hydration, steps, heart rate, screen time).
- **AI-Powered Wellness Reports:**
  - Integrates with HuggingFace Hub's `InferenceClient` (using `mistralai/Mistral-7B-Instruct` or other LLM configurations).
  - Automatically compiles daily or weekly telemetry context.
  - Generates comprehensive wellness reports outlining lifestyle trends, risk flags (without diagnosing diseases), and actionable wellness recommendations.
- **Anomaly Detection:** Flags telemetry entries with abnormal values (e.g. Heart Rate > 110, Sleep < 240 mins, Steps < 1000) and displays warning banners.
- **7-day Trends:** Displays historical telemetry sparklines and interactive line charts for family members.
- **Fallback Simulation:** Automatically provides realistic simulated mock data if no database logs are present for the current day.

---

### Feature 3 — SOS Emergency System
- **Emergency Panic Button:** Triggers a high-priority SOS emergency signal.
- **GPS Coordinates & Live Map:** Uses `streamlit-geolocation` to acquire coordinates and maps them using `st.map`.
- **Nominatim Reverse Geocoding:** Uses the OpenStreetMap Nominatim reverse API to resolve coordinate coordinates into street addresses (cached for 24 hours).
- **Audible Siren Alert:** Loops an audible siren audio alarm (`Emergency_siren.ogg`) on all family members' screens while an emergency is active.
- **Background Fallbacks:** Sends an instant WebSocket broadcast and queues Twilio SMS alerts (if credentials are set).
- **Resolve:** Active emergencies can be marked as resolved.

---

### Feature 4 — Secure Document Vault
- **Dual-Gate Access Control:** Access requires both the user's password and the answer to a dynamically selected family security question.
- **AES-256-CBC Encryption:** Files are encrypted with AES-256-CBC using keys derived from the vault password and unique initialization vectors (IVs).
- **Zero-Footprint Streaming:** Decryption occurs entirely in-memory during downloads, ensuring plaintext is never written to disk.
- **File Management & Organization:** Files can be uploaded, deleted, and filtered by categories (`IDs`, `Medical`, `Legal`, `Insurance`, `Other`).
- **Session Auto-Expiry:** Sessions expire automatically after a configurable period (default: 10 mins).

---

### Feature 5 — AI Privacy Shield
A multi-stage image-hardening pipeline designed to sanitize media files before sharing them on social platforms.

#### Pipeline Stages
1. **Metadata Sanitization:** Strips all EXIF, IPTC, and XMP metadata (GPS, timestamps, device profiles).
2. **Object & Face Detection:**
   - Uses OpenCV Haar Cascades for facial detection.
   - Uses YOLOv8 (`yolov8n.pt`) to detect sensitive objects (cell phones, laptops, TVs, signs, and vehicles).
   - Uses EasyOCR to scan and isolate textual content within images.
3. **Semantic Redaction:** Selectively blurs detected faces and pixelates text regions, license plates, and sensitive objects.
4. **Obfuscation Noise Layer:** Inject structured line overlays and randomized Gaussian noise to disrupt face-recognition embeddings and automated scrapers.

#### Privacy Modes
- **Family Safe:** Blurs detected faces; retains text and vehicle context.
- **Social Media:** Blurs faces, text, and vehicle context.
- **Strict:** Applies heavier blurring, pixelation, and noise overlays.

#### Backend API
- **Endpoint:** `POST /privacy/protect`
- **Form Fields:** `file` (binary), `blur_targets` (string `true`/`false`), `adversarial_noise` (string `true`/`false`), `use_pgd` (string `true`/`false`).
- **Response Headers:**
  - `X-Privacy-Report`: JSON-serialized summary of the hardening metrics (faces, text, objects detected, risk scores before/after).
  - `X-Privacy-Mode`: The active privacy protection profile.

---

## Running Tests

Verify the backend modules using unit tests:

```bash
# Activate the virtual environment
source venv/bin/activate

# Execute unit tests
python -m pytest tests/ -v
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Ensure you run all commands from the `kinnect/` root directory. |
| `aiomysql.OperationalError` | Check DB credentials in `.env`, and verify the local MySQL service is active. |
| YOLO weights download fails | Set `YOLO_MODEL=yolov8n.pt` to auto-download on startup (requires internet). |
| `pyheif` installation fails | HEIC support is optional. Install `libheif` on your OS first, or skip it. |
| Vault security question missing | Seed your database table `vault_security_questions` with questions and answer hashes. |
| AI Report is empty | Verify your `HF_API_TOKEN` and model settings in `.env` are valid. |
