#!/usr/bin/env python3
"""Sales Agent Tizimi — Bir martalik sozlash skripti"""
import os
import sys
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"
PRODUCT_CONFIG = BASE_DIR / "product_config.json"


def step(msg):
    print(f"\n[{chr(9989)}] {msg}...")


def run(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def main():
    print("""
    ╔══════════════════════════════════════════╗
    ║    Sales Agent Tizimi v1.0               ║
    ║    O'zbekiston bozori uchun AI sales     ║
    ╚══════════════════════════════════════════╝
    """)

    # 1. Virtual environment
    venv_dir = BASE_DIR / "venv"
    if not venv_dir.exists():
        step("Virtual environment yaratilmoqda")
        run(f"python3 -m venv {venv_dir}")
    
    pip = str(venv_dir / "bin" / "pip")
    python = str(venv_dir / "bin" / "python")

    # 2. Install dependencies
    step("Kutubxonalar o'rnatilmoqda")
    r = run(f"{pip} install -q -r {BASE_DIR / 'requirements.txt'}")
    if r.returncode != 0:
        print(f"  Xato: {r.stderr}")
        return

    # 3. .env file
    if not ENV_FILE.exists():
        step(".env fayli yaratilmoqda")
        shutil = __import__("shutil")
        shutil.copy(str(ENV_EXAMPLE), str(ENV_FILE))

    # 4. Check API keys
    env_content = ENV_FILE.read_text()
    has_anthropic = "ANTHROPIC_API_KEY=" in env_content and "sk-ant-" in env_content and "..." not in env_content.split("ANTHROPIC_API_KEY=")[1].split("\n")[0]
    if not has_anthropic:
        print("""
    [!] ANTHROPIC_API_KEY topilmadi!
        Simulation mode ishlaydi (mock ma'lumot).
        Haqiqiy lead va email uchun:
        1. https://console.anthropic.com da ro'yxatdan o'ting
        2. API Key yarating
        3. .env fayliga qo'ying: ANTHROPIC_API_KEY=sk-ant-...
        """)

    # 5. Product config
    if PRODUCT_CONFIG.exists():
        step("IT maxsulotingiz sozlamalari")
        try:
            config = json.loads(PRODUCT_CONFIG.read_text())
            print(f"  Maxsulot: {config.get('product_name', 'N/A')}")
            print(f"  Kompaniya: {config.get('company_name', 'N/A')}")
            edit = input("\n  O'zgartirish kerakmi? (y/N): ").lower().strip()
            if edit == 'y':
                config['product_name'] = input(f"  Maxsulot nomi [{config['product_name']}]: ") or config['product_name']
                config['product_description'] = input(f"  Tavsif [{config['product_description']}]: ") or config['product_description']
                config['company_name'] = input(f"  Kompaniya nomi [{config['company_name']}]: ") or config['company_name']
                PRODUCT_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False))
                print("  Saqlandi!")
        except Exception as e:
            print(f"  Xato: {e}")

    # 6. Playwright browsers
    step("Playwright brauzerlar tekshirilmoqda")
    r = run(f"{python} -m playwright install chromium 2>/dev/null")
    if r.returncode == 0:
        print("  Brauzer tayyor")

    # 7. Initialize database
    step("Ma'lumotlar bazasi tayyorlanmoqda")
    r = run(f"{python} -c \"from database import init_db; init_db()\"", cwd=str(BASE_DIR))

    print(f"""
    ╔══════════════════════════════════════════╗
    ║   Tayyor! Serverni ishga tushiring:      ║
    ║                                          ║
    ║   {BASE_DIR / 'run.sh'}              ║
    ║                                          ║
    ║   Dashboard: http://localhost:8000/      ║
    ╚══════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
