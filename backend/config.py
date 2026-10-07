import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Fact₹1"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    SECRET_KEY: str = "fact1_super_secret_signing_key_secure_2026"
    FRONTEND_URL: str = "http://localhost:8000"
    BACKEND_URL: str = "http://localhost:8000"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./fact1.db"
    
    # Payment Gateway Configuration
    # Mode can be 'cashfree', 'simulator', or 'razorpay'
    PAYMENT_MODE: str = "simulator"
    
    # Cashfree Payments Settings
    CASHFREE_APP_ID: str = "placeholder_cashfree_app_id"
    CASHFREE_SECRET_KEY: str = "placeholder_cashfree_secret_key"
    CASHFREE_ENV: str = "sandbox"  # 'sandbox' or 'production'
    CASHFREE_API_VERSION: str = "2023-08-01"
    
    # Razorpay Settings (Secondary / Alternate)
    PAYMENT_KEY_ID: str = "rzp_test_placeholder_key_id"
    PAYMENT_KEY_SECRET: str = "placeholder_secret_key"
    PAYMENT_WEBHOOK_SECRET: str = "placeholder_webhook_secret"
    
    # Admin Security
    ADMIN_SECRET_KEY: str = "admin_fact1_secure_key_2026"
    
    # Pricing & Currency
    DEFAULT_FACT_PRICE_PAISE: int = 100  # 100 paise = ₹1.00
    CURRENCY: str = "INR"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


settings = Settings()
