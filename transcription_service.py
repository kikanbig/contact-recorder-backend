#!/usr/bin/env python3
"""
Упрощенный сервис транскрипции через faster-whisper
Обрабатывает аудио файлы с детальными логами
"""

import sys
import os
import json
import tempfile
import traceback

# Детальная диагностика версий библиотек
def diagnose_system():
    """Диагностика системы и версий библиотек"""
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ:", file=sys.stderr)
    print(f"🐍 Python версия: {sys.version}", file=sys.stderr)
    
    try:
        import torch
        print(f"🔥 PyTorch версия: {torch.__version__}", file=sys.stderr)
        print(f"🔥 PyTorch CUDA доступен: {torch.cuda.is_available()}", file=sys.stderr)
    except ImportError as e:
        print(f"❌ PyTorch не найден: {e}", file=sys.stderr)
        return False
    
    try:
        import faster_whisper
        print(f"🎤 faster-whisper импортирован успешно", file=sys.stderr)
    except ImportError as e:
        print(f"❌ faster-whisper не найден: {e}", file=sys.stderr)
        return False
    
    try:
        import librosa
        print(f"🎵 librosa версия: {librosa.__version__}", file=sys.stderr)
    except ImportError as e:
        print(f"❌ librosa не найден: {e}", file=sys.stderr)
        return False
    
    return True

# Импортируем библиотеки с диагностикой
try:
    import torch
    from faster_whisper import WhisperModel
    import librosa
    import soundfile as sf
    from pathlib import Path
    
    print("✅ Все библиотеки импортированы успешно", file=sys.stderr)
    
except ImportError as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ИМПОРТА: {e}", file=sys.stderr)
    print(f"❌ Трейсбек: {traceback.format_exc()}", file=sys.stderr)
    sys.exit(1)

def transcribe_audio_simple(audio_data, language='ru', model_size='small'):
    """
    Транскрибирует аудио данные через faster-whisper
    
    Args:
        audio_data: Бинарные данные аудио файла
        language: Язык для транскрипции (по умолчанию 'ru')
        model_size: Размер модели ('tiny', 'base', 'small', 'medium', 'large')
    
    Returns:
        dict: {'success': bool, 'text': str, 'segments': list, 'error': str}
    """
    try:
        print(f"🚀 Загружаем faster-whisper модель: {model_size}", file=sys.stderr)
        
        # Определяем устройство
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        print(f"💻 Используем устройство: {device} с типом вычислений: {compute_type}", file=sys.stderr)
        
        # Создаем временный файл для аудио
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            # 1. Загружаем модель faster-whisper
            print("📥 Шаг 1: Загружаем модель faster-whisper...", file=sys.stderr)
            try:
                model = WhisperModel(model_size, device=device, compute_type=compute_type)
                print("✅ Модель faster-whisper загружена", file=sys.stderr)
            except Exception as model_error:
                print(f"❌ Ошибка загрузки модели faster-whisper: {model_error}", file=sys.stderr)
                print(f"❌ Трейсбек модели: {traceback.format_exc()}", file=sys.stderr)
                raise
            
            # 2. Выполняем транскрипцию
            print(f"🎯 Шаг 2: Выполняем транскрипцию файла: {temp_path}", file=sys.stderr)
            try:
                segments, info = model.transcribe(temp_path, language=language)
                print(f"✅ Транскрипция завершена, язык: {info.language}, вероятность: {info.language_probability:.2f}", file=sys.stderr)
            except Exception as transcribe_error:
                print(f"❌ Ошибка транскрипции: {transcribe_error}", file=sys.stderr)
                print(f"❌ Трейсбек транскрипции: {traceback.format_exc()}", file=sys.stderr)
                raise
            
            # 3. Обрабатываем результаты
            print("📊 Шаг 3: Обрабатываем результаты...", file=sys.stderr)
            
            full_text = ""
            segments_list = []
            
            for segment in segments:
                text = segment.text.strip()
                start = segment.start
                end = segment.end
                
                full_text += text + " "
                segments_list.append({
                    "text": text,
                    "start": start,
                    "end": end
                })
            
            full_text = full_text.strip()
            
            print(f"🎉 faster-whisper транскрипция УСПЕШНО завершена!", file=sys.stderr)
            print(f"📝 Сегментов: {len(segments_list)}", file=sys.stderr)
            print(f"📄 Символов: {len(full_text)}", file=sys.stderr)
            print(f"🌍 Язык: {info.language} (вероятность: {info.language_probability:.2f})", file=sys.stderr)
            
            return {
                'success': True,
                'text': full_text,
                'segments': segments_list,
                'speakers': [],
                'speaker_count': 0,
                'language': info.language,
                'language_probability': info.language_probability,
                'error': None,
                'method': 'faster-whisper'
            }
        
        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_path)
                print(f"🗑️ Временный файл удален: {temp_path}", file=sys.stderr)
            except Exception as cleanup_error:
                print(f"⚠️ Ошибка удаления временного файла: {cleanup_error}", file=sys.stderr)
                
    except Exception as e:
        error_message = str(e)
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА faster-whisper: {error_message}", file=sys.stderr)
        print(f"❌ Тип ошибки: {type(e).__name__}", file=sys.stderr)
        print(f"❌ Полный трейсбек: {traceback.format_exc()}", file=sys.stderr)
        return {
            'success': False,
            'text': '',
            'segments': [],
            'speakers': [],
            'speaker_count': 0,
            'error': error_message,
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc(),
            'method': 'faster-whisper'
        }

def transcribe_audio(audio_data, language='ru', model_size='small'):
    """
    Обратная совместимость - вызывает упрощенную функцию транскрипции
    """
    return transcribe_audio_simple(audio_data, language, model_size)

def main():
    """
    Основная функция для вызова из Node.js
    Ожидает путь к аудио файлу как аргумент командной строки
    """
    # Выполняем диагностику системы
    if not diagnose_system():
        print(json.dumps({
            'success': False,
            'error': 'Системная диагностика не прошла'
        }, ensure_ascii=False))
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print(json.dumps({
            'success': False,
            'error': 'Не указан путь к аудио файлу'
        }, ensure_ascii=False))
        sys.exit(1)
    
    audio_file_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else 'ru'
    model_size = sys.argv[3] if len(sys.argv) > 3 else 'small'
    
    try:
        print(f"📂 Читаем аудио файл: {audio_file_path}", file=sys.stderr)
        
        # Читаем аудио файл
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        
        print(f"📦 Размер аудио файла: {len(audio_data)} байт", file=sys.stderr)
        
        # Транскрибируем с faster-whisper
        result = transcribe_audio_simple(audio_data, language, model_size)
        
        # Выводим результат в JSON формате для Node.js (только в stdout)
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': f'Ошибка чтения файла: {str(e)}',
            'traceback': traceback.format_exc()
        }, ensure_ascii=False))
        sys.exit(1)

if __name__ == '__main__':
    main() 