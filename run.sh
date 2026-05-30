#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== Sales Agent Tizimi v1.0 ==="
echo ""

if [ ! -d "venv" ]; then
    echo "[1/3] Virtual environment yaratilmoqda..."
    python3 -m venv venv
fi

source venv/bin/activate

if [ ! -f ".env" ]; then
    echo "[!] .env fayli topilmadi. .env.example dan nusxa olinmoqda..."
    cp .env.example .env
    echo "[!] Iltimos, .env faylini ochib API kalitlarni kiriting!"
    echo "    nano .env"
    exit 1
fi

echo "[2/3] Kutubxonalar tekshirilmoqda..."
pip install -q -r requirements.txt 2>/dev/null || pip install -r requirements.txt

echo "[3/3] Serverni ishga tushirish..."
echo "    Dashboard: http://localhost:8000/"
echo "    API docs:   http://localhost:8000/docs"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
