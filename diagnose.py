"""
Діагностика: перевіряє довжину транскриптів і що саме передається в LLM.
Запускати з кореня проекту: python3 diagnose.py
"""
from pathlib import Path
import sys

# Знаходимо папку downloads/ (де лежать транскрипти)
DOWNLOADS = Path("downloads")

if not DOWNLOADS.exists():
    print("❌ Папка downloads/ не знайдена. Запусти з кореня проекту.")
    sys.exit(1)

# Шукаємо .txt файли (транскрипти)
txt_files = sorted(DOWNLOADS.glob("*.txt"))

if not txt_files:
    print("❌ Транскрипти (.txt) не знайдені в downloads/")
    print("   Перевір: ls downloads/")
    sys.exit(1)

print(f"✅ Знайдено {len(txt_files)} транскриптів\n")
print("=" * 70)

for txt_path in txt_files:
    text = txt_path.read_text(encoding="utf-8")
    chars = len(text)
    words = len(text.split())
    # Груба оцінка токенів: 1 токен ≈ 2-3 символи для української
    approx_tokens = chars // 2.5

    print(f"\n📄 {txt_path.name}")
    print(f"   Символів: {chars}")
    print(f"   Слів: {words}")
    print(f"   Приблизно токенів: {int(approx_tokens)}")
    print(f"   ── Перші 300 символів ──")
    print(f"   {text[:300]}...")
    print(f"   ── Середина (символи {chars//2 - 150}–{chars//2 + 150}) ──")
    middle = text[chars//2 - 150:chars//2 + 150]
    print(f"   ...{middle}...")
    print(f"   ── Останні 300 символів ──")
    print(f"   ...{text[-300:]}")

print("\n" + "=" * 70)
print("\n🔍 ВИСНОВКИ:")
avg_chars = sum(len(p.read_text(encoding='utf-8')) for p in txt_files) / len(txt_files)
print(f"   Середня довжина: {int(avg_chars)} символів")
print(f"   Середня кількість токенів: ~{int(avg_chars / 2.5)}")

if avg_chars < 1000:
    print("   ⚠️  ПІДОЗРІЛО КОРОТКО — Whisper можливо обрізає або не розпізнає")
elif avg_chars > 8000:
    print("   ⚠️  ДОВГО — можливі проблеми з 'lost in the middle' у Qwen 7B")
else:
    print("   ✅ Нормальна довжина для аналізу")