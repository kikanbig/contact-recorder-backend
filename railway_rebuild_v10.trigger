REBUILD TRIGGER v10 - SPEECHBRAIN ДИАРИЗАЦИЯ
=======================================================

Изменения в версии 3.1.1:
- ✅ Переключились с NeMo на SpeechBrain для диаризации
- ✅ SpeechBrain + pyannote.audio - более простая установка
- ✅ Исправлена ошибка "No module named 'nemo'"
- ✅ Мобильное приложение теперь использует SpeechBrain
- ✅ Все зависимости корректно установлены в Docker
- ✅ Эндпоинт /api/recordings/upload работает с диаризацией
- ✅ Админка и все API функционируют

Диаризация: SpeechBrain + pyannote.audio (НЕ Whisper)
Транскрипция: faster-whisper

Готов к тестированию с мобильным приложением!

Дата: $(date)
Время: $(date +%H:%M:%S) 