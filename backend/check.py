"""
check.py — Diagnóstico rápido do ambiente Jarvis.
Rode: python backend/check.py
"""
import sys
print(f"Python: {sys.version}")

errors = []

def check(name, import_str):
    try:
        exec(import_str)
        print(f"  ✅ {name}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        errors.append((name, str(e)))

print("\n── Dependências ──")
check("fastapi",          "import fastapi")
check("uvicorn",          "import uvicorn")
check("pydantic",         "import pydantic")
check("python-dotenv",    "from dotenv import load_dotenv")
check("google-generativeai", "import google.generativeai")
check("openai",           "import openai")
check("pyttsx3",          "import pyttsx3")
check("speech_recognition","import speech_recognition")
check("supabase",         "from supabase import create_client")

print("\n── Módulos do Jarvis ──")
sys.path.insert(0, "backend")
check("config",    "import config; print(f'    GEMINI_KEY set: {bool(config.GEMINI_API_KEY)}')")
check("database",  "import database")
check("ai",        "import ai")
check("voice",     "import voice")
check("commands",  "import commands")
check("tasks",     "import tasks")

if errors:
    print(f"\n⚠️  {len(errors)} erro(s) encontrado(s). Instale as dependências faltantes.")
    print("   pip install -r backend/requirements.txt")
else:
    print("\n✅ Tudo ok! Backend pronto para rodar.")
