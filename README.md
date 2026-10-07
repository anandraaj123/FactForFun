# Fact₹1 (Fact-One) 💡

> **"One rupee. One new thing."**  
> Pay ₹1. Satisfy your curiosity. Learn something genuine you didn't know 10 seconds ago.

🔗 **Link:** [factforfun-production.up.railway.app](factforfun-production.up.railway.app)

---

## ⚡ Product Philosophy

**Fact₹1** is an ultra-minimalist, lightning-fast micro-learning web app designed primarily for Indian users.

* **Frictionless:** No registration or passwords required to unlock facts.
* **Affordable:** Exactly **₹1 (100 paise)** per verified curiosity.
* **High Quality:** 100+ vetted, fascinating facts with verified institutional sources (NASA, Smithsonian, Nature, ISRO, Nobel Prize, etc.) — **no runtime LLM hallucinations**.
* **Zero Bloat:** Pure HTML5, CSS3, Vanilla JavaScript, FastAPI, and SQLite/PostgreSQL. Zero heavy frontend framework overhead for instant (<50ms) page loads on low-end mobile devices.
* **Instant Social Sharing:** Includes client-rendered 1080x1080px Canvas social image generator for WhatsApp & Twitter.

---

## 🏗️ Architecture & Stack

* **Backend:** Python 3.10+ / FastAPI (REST API with rate-limiting, CORS, and Pydantic validation)
* **Database:** SQLite (Local Dev) / PostgreSQL (Production via async SQLAlchemy + aiosqlite / asyncpg)
* **Payment Processing:** Razorpay Orders API + HMAC-SHA256 signature verification (with a built-in Payment Simulator for instant local development)
* **Frontend:** Semantic HTML5, Modern CSS (Glassmorphism, Dark/Light modes, Apple-style micro-interactions), Vanilla JS
* **Testing:** Pytest, pytest-asyncio, HTTPX

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Enter Project Directory
```bash
git clone https://github.com/your-username/fact-one.git
cd fact-one
```

### 2. Create and Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

The default `.env` includes `PAYMENT_MODE=simulator` which enables local testing out-of-the-box without needing a live Razorpay merchant account immediately.

### 5. Run the Application
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at:
* **App:** [http://localhost:8000](http://localhost:8000)
* **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Admin Dashboard:** [http://localhost:8000/admin](http://localhost:8000/admin) *(Default Admin Key: `admin_fact1_secure_key_2026`)*

---

## 🧪 Running the Automated Test Suite

Run full asynchronous test suite covering fact security, payment verification, session isolation, and admin controls:

```bash
pytest
```

---

## 💳 Payment Gateway Setup (Razorpay)

To switch from the built-in Simulator to live or sandbox Razorpay:

1. Create a free account at [Razorpay Dashboard](https://dashboard.razorpay.com/).
2. Generate API Keys under **Settings > API Keys** (Test Mode).
3. Update `.env`:
   ```env
   PAYMENT_MODE=razorpay
   PAYMENT_KEY_ID=rzp_test_YOUR_KEY_ID
   PAYMENT_KEY_SECRET=YOUR_KEY_SECRET
   PAYMENT_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET
   ```
4. Restart Uvicorn. The frontend will automatically load the official Razorpay Checkout SDK.

---

## 🛡️ Security Architecture

* **Server-Side Verification Only:** The client never dictates whether a fact is unlocked. Unlocking requires server-side HMAC-SHA256 signature verification matching order IDs.
* **Gated Fact Content:** Locked fact queries (`GET /api/facts/teaser`) strip out `fact_text` and `explanation`. Full fact content (`GET /api/facts/{id}`) strictly checks the user's DB unlock record.
* **Session Integrity:** Orders are bound to unique cryptographic session identifiers.
* **Rate Limiting:** SlowAPI enforces rate limits on payment creation and fact querying to prevent automated scraping or brute force.
* **Parameterized Queries:** Async SQLAlchemy protects against SQL injection.

---

## 📂 Project Structure

```text
fact-one/
├── backend/
│   ├── config.py              # Environment configuration (Pydantic Settings)
│   ├── database.py            # Async SQLAlchemy engine & session factory
│   ├── models.py              # Fact, Order, FactUnlock, Analytics models
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── security.py            # HMAC verification & admin auth
│   ├── main.py                # FastAPI app & routing
│   ├── routes/
│   │   ├── facts.py           # Teaser, locked/unlocked, categories API
│   │   ├── payments.py        # Order creation, verification, webhooks
│   │   ├── admin.py           # Admin metrics and fact CRUD
│   │   └── analytics.py       # Funnel event tracker
│   └── services/
│       ├── fact_service.py    # Fact selection & curation logic
│       ├── payment_service.py # Gateway integration (Razorpay + Simulator)
│       ├── unlock_service.py  # Fact unlock records
│       └── analytics_service.py # Privacy-safe analytics
├── frontend/
│   ├── index.html             # Minimalist mobile-first landing & fact card
│   ├── admin.html             # Admin portal
│   ├── css/
│   │   └── style.css          # Responsive typography & design system
│   ├── js/
│   │   ├── app.js             # Core client interaction & payment flow
│   │   └── card_generator.js  # Dynamic 1080x1080 canvas share card generator
│   ├── favicon.svg            # SVG brand icon
│   ├── robots.txt             # SEO Crawler directives
│   └── sitemap.xml            # Search engine sitemap
├── data/
│   ├── seed_facts.json        # 100+ verified facts across 17 categories
│   └── init_db.py             # Automatic schema & seed data loader
├── tests/
│   ├── conftest.py            # Async test fixtures
│   ├── test_facts.py          # Fact API & security gate tests
│   ├── test_payments.py       # Order & signature verification tests
│   └── test_security.py       # Admin & session isolation tests
├── .env.example
├── .gitignore
├── requirements.txt
├── pytest.ini
├── README.md
└── DEPLOYMENT.md
```

---

## 📜 License
MIT License. Built for curious minds everywhere.
