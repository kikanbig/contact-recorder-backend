#!/usr/bin/env python3
"""
Локальный сервис транскрипции через OpenAI Whisper
Обрабатывает аудио файлы без интернет соединения
"""

import sys
import os
import json
import whisper
import tempfile
from pathlib import Path

def transcribe_audio(audio_data, language='ru', model_size='small'):
    """
    Транскрибирует аудио данные через локальный Whisper
    
    Args:
        audio_data: Бинарные данные аудио файла
        language: Язык для транскрипции (по умолчанию 'ru')
        model_size: Размер модели ('tiny', 'base', 'small', 'medium', 'large')
    
    Returns:
        dict: {'success': bool, 'text': str, 'error': str}
    """
    try:
        print(f"🤖 Загружаем модель Whisper: {model_size}", file=sys.stderr)
        
        # Загружаем модель Whisper (скачается автоматически при первом запуске)
        model = whisper.load_model(model_size)
        
        print(f"✅ Модель {model_size} загружена", file=sys.stderr)
        
        # Создаем временный файл для аудио
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            print(f"🎵 Транскрибируем аудио файл: {temp_path}", file=sys.stderr)
            
            # Выполняем транскрипцию
            result = model.transcribe(
                temp_path,
                language=language,
                fp16=False,  # Отключаем FP16 для совместимости
                verbose=False
            )
            
            transcription_text = result['text'].strip()
            
            print(f"✅ Транскрипция завершена: {len(transcription_text)} символов", file=sys.stderr)
            
            return {
                'success': True,
                'text': transcription_text,
                'language': result.get('language', language),
                'error': None
            }
        
        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        error_message = str(e)
        print(f"❌ Ошибка транскрипции: {error_message}", file=sys.stderr)
        return {
            'success': False,
            'text': '',
            'error': error_message
        }

def main():
    """
    Основная функция для вызова из Node.js
    Ожидает путь к аудио файлу как аргумент командной строки
    """
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
        
        # Транскрибируем
        result = transcribe_audio(audio_data, language, model_size)
        
        # Выводим результат в JSON формате для Node.js (только в stdout)
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': f'Ошибка чтения файла: {str(e)}'
        }, ensure_ascii=False))
        sys.exit(1)

if __name__ == '__main__':
    main() 