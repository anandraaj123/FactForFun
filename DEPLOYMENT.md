# Fact₹1 — Production Deployment Guide 🚀

This guide walks you through deploying **Fact₹1** to production on popular cloud providers (e.g. **Render**, **Railway**, **DigitalOcean**, or any Ubuntu VPS) with custom domain support and live Razorpay payments.

---

## 1. Prerequisites

1. A GitHub repository containing this codebase.
2. A registered custom domain (e.g. `fact1.in` or `onefact.in` from Namecheap / GoDaddy / Cloudflare).
3. A live merchant account with [Razorpay](https://razorpay.com/) (or PhonePe / Cashfree).
4. Cloud hosting account (e.g., Render, Railway, DigitalOcean, AWS).

---

## 2. Option A: One-Click Deployment on Render.com (Recommended)

Render offers zero-DevOps deployment for FastAPI + PostgreSQL + Static frontend.

### Step 1: Create a PostgreSQL Database
1. Go to your [Render Dashboard](https://dashboard.render.com/) and click **New + > PostgreSQL**.
2. Name: `fact1-db`
3. Region: `Singapore (ap-southeast-1)` or closest to India for minimal latency.
4. Copy the **Internal Database URL** (e.g., `postgresql+asyncpg://fact1_user:password@host/fact1_db`).

### Step 2: Create a Web Service
1. Click **New + > Web Service** and connect your GitHub repository.
2. Configure settings:
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt asyncpg`
   * **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Add Environment Variables in the Render UI:
   ```env
   APP_ENV=production
   DEBUG=False
   DATABASE_URL=postgresql+asyncpg://fact1_user:password@host/fact1_db
   SECRET_KEY=generate_a_secure_random_64_char_key
   ADMIN_SECRET_KEY=your_strong_admin_key_here
   PAYMENT_MODE=razorpay
   PAYMENT_KEY_ID=rzp_live_xxxxxxxxxxxx
   PAYMENT_KEY_SECRET=your_live_key_secret
   PAYMENT_WEBHOOK_SECRET=your_live_webhook_secret
   FRONTEND_URL=https://fact1.in
   BACKEND_URL=https://fact1.in
   ```
4. Click **Deploy Web Service**.

---

## 3. Option B: Linux VPS / Ubuntu Deployment (DigitalOcean / AWS EC2)

### Step 1: System Setup
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx certbot python3-certbot-nginx git -y
```

### Step 2: Clone & Virtual Environment
```bash
cd /var/www
sudo git clone https://github.com/your-username/fact-one.git fact1
cd fact1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Systemd Service
Create `/etc/systemd/system/fact1.service`:
```ini
[Unit]
Description=Fact₹1 FastAPI Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/fact1
EnvironmentFile=/var/www/fact1/.env
ExecStart=/var/www/fact1/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 4

[Install]
WantedBy=multi-user.target
```

Start and enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl start fact1
sudo systemctl enable fact1
```

### Step 4: Nginx Reverse Proxy Configuration
Create `/etc/nginx/sites-available/fact1`:
```nginx
server {
    server_name fact1.in www.fact1.in;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site and test Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/fact1 /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 5: HTTPS SSL Certificate with Let's Encrypt
```bash
sudo certbot --nginx -d fact1.in -d www.fact1.in
```

---

## 4. Configuring Cashfree Payments (PG v2023-08-01)

1. Log in to your [Cashfree Merchant Dashboard](https://merchant.cashfree.com/).
2. Navigate to **Payment Gateway > Developers > API Keys**.
3. Copy your **App ID** (`CASHFREE_APP_ID`) and **Secret Key** (`CASHFREE_SECRET_KEY`).
4. Set in your production `.env`:
   ```env
   PAYMENT_MODE=cashfree
   CASHFREE_APP_ID=your_cashfree_app_id
   CASHFREE_SECRET_KEY=your_cashfree_secret_key
   CASHFREE_ENV=production  # or 'sandbox' for test mode
   CASHFREE_API_VERSION=2023-08-01
   ```
5. Navigate to **Payment Gateway > Developers > Webhooks** and add your webhook endpoint:
   * **Webhook URL:** `https://fact1.in/api/payments/cashfree-webhook`
   * **Events:** Check `PAYMENT_SUCCESS_WEBHOOK` / `ORDER_PAID`.

---

## 4.1 Configuring Razorpay Payments (Alternate Option)

1. Log in to [Razorpay Merchant Dashboard](https://dashboard.razorpay.com/).
2. Switch to **Live Mode** and go to **Settings > API Keys** to generate **Key ID** and **Key Secret**.
3. Set `PAYMENT_MODE=razorpay` in `.env`.
4. Add Webhook at `https://fact1.in/api/payments/webhook`.

---

## 5. Pre-Launch Verification Checklist

- [ ] HTTPS is active with a valid SSL certificate.
- [ ] Database is initialized with seed facts (`python -m data.init_db`).
- [ ] Tested live payment with ₹1 on a real mobile device via UPI (GPay/PhonePe).
- [ ] Fact reveal animation triggers smoothly.
- [ ] Source attribution link redirects to official source.
- [ ] Visual card generator renders and downloads crisp PNG.
- [ ] Admin portal is protected behind `ADMIN_SECRET_KEY`.
- [ ] Robots.txt and Sitemap.xml are accessible at `/robots.txt` and `/sitemap.xml`.
