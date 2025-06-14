#!/usr/bin/env python3
"""
Упрощенный сервис транскрипции через WhisperX
Только базовая транскрипция без диаризации
"""

import sys
import os
import json
import tempfile
import torch
import whisperx
from pathlib import Path

def transcribe_audio_simple(audio_data, language='ru', model_size='small'):
    """
    Транскрибирует аудио данные через WhisperX (только транскрипция)
    
    Args:
        audio_data: Бинарные данные аудио файла
        language: Язык для транскрипции (по умолчанию 'ru')
        model_size: Размер модели ('tiny', 'base', 'small', 'medium', 'large')
    
    Returns:
        dict: {'success': bool, 'text': str, 'error': str}
    """
    try:
        print(f"🚀 Загружаем WhisperX модель: {model_size}", file=sys.stderr)
        
        # Определяем устройство
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        print(f"💻 Используем устройство: {device} с типом вычислений: {compute_type}", file=sys.stderr)
        
        # Создаем временный файл для аудио
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            # 1. Загружаем модель WhisperX
            model = whisperx.load_model(model_size, device, compute_type=compute_type, language=language)
            
            # 2. Загружаем аудио
            print(f"🎵 Загружаем аудио файл: {temp_path}", file=sys.stderr)
            audio = whisperx.load_audio(temp_path)
            
            # 3. Выполняем транскрипцию
            print("🎯 Выполняем транскрипцию...", file=sys.stderr)
            result = model.transcribe(audio, batch_size=16)
            
            # Собираем текст из сегментов
            full_text = ""
            for segment in result["segments"]:
                full_text += segment["text"]
            
            full_text = full_text.strip()
            
            print(f"✅ WhisperX транскрипция завершена", file=sys.stderr)
            print(f"📄 Символов: {len(full_text)}", file=sys.stderr)
            
            return {
                'success': True,
                'text': full_text,
                'language': language,
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
        print(f"❌ Ошибка WhisperX транскрипции: {error_message}", file=sys.stderr)
        return {
            'success': False,
            'text': '',
            'error': error_message
        }

def transcribe_audio(audio_data, language='ru', model_size='small'):
    """
    Обратная совместимость
    """
    return transcribe_audio_simple(audio_data, language, model_size)

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
        
        # Транскрибируем с WhisperX
        result = transcribe_audio_simple(audio_data, language, model_size)
        
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