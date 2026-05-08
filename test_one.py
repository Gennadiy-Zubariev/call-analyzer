from pathlib import Path
from src.analyzer import OllamaAnalyzer
from config import settings

# Знайдемо перший доступний транскрипт автоматично
DOWNLOADS = Path("downloads")
txt_files = sorted(DOWNLOADS.glob("*.txt"))

if not txt_files:
    print("❌ Транскрипти .txt не знайдені в downloads/")
    raise SystemExit(1)

print(f"📁 Знайдено {len(txt_files)} транскриптів:")
for i, f in enumerate(txt_files):
    print(f"   {i}: {f.name} ({len(f.read_text(encoding='utf-8'))} символів)")

# Беремо найдовший транскрипт — там найбільше шансів побачити різницю
target = max(txt_files, key=lambda p: len(p.read_text(encoding='utf-8')))
print(f"\n🎯 Тестую на найдовшому: {target.name}")

transcript = target.read_text(encoding="utf-8")
print(f"📏 Довжина: {len(transcript)} символів")
print(f"📝 Перші 300 символів:\n   {transcript[:300]}...\n")

print("=" * 70)
print("⏳ Аналізую через Ollama (займе 10-30 секунд)...")
print("=" * 70)

analyzer = OllamaAnalyzer(host=settings.ollama_host, model=settings.ollama_model)
result = analyzer.analyze(transcript)

print("\n" + "=" * 70)
print("✅ РЕЗУЛЬТАТ JSON:")
print("=" * 70)
print(result.model_dump_json(indent=2))

print("\n" + "=" * 70)
print("📊 ШВИДКА ОЦІНКА:")
print("=" * 70)
print(f"   Менеджер:        {result.manager or '(не визначено)'}")
print(f"   Тип дзвінка:     {result.call_type}")
print(f"   Тип роботи:      {result.work_type}")
print(f"   Сума балів:      {result.total_score}/8")
print(f"   Загальна оцінка: {result.score}/10")
print(f"   Проблемний:      {result.is_problematic}")
print(f"   Коментар:        {result.comment}")

if "[АВТО-ФОЛБЕК]" in result.comment:
    print("\n⚠️  УВАГА: спрацював fallback! LLM не зміг проаналізувати.")
else:
    print("\n✅ LLM відпрацював без fallback.")