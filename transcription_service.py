#!/usr/bin/env python3
"""
Полноценный сервис транскрипции через WhisperX с диаризацией
Обрабатывает аудио файлы с разделением по говорящим
"""

import sys
import os
import json
import tempfile
import torch
import whisperx
from pathlib import Path

def transcribe_audio_with_diarization(audio_data, language='ru', model_size='small'):
    """
    Транскрибирует аудио данные через WhisperX с полной диаризацией
    
    Args:
        audio_data: Бинарные данные аудио файла
        language: Язык для транскрипции (по умолчанию 'ru')
        model_size: Размер модели ('tiny', 'base', 'small', 'medium', 'large')
    
    Returns:
        dict: {'success': bool, 'text': str, 'segments': list, 'speakers': list, 'error': str}
    """
    try:
        print(f"🚀 Загружаем WhisperX модель: {model_size}", file=sys.stderr)
        print(f"👥 Диаризация: ВКЛЮЧЕНА", file=sys.stderr)
        
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
            print("📥 Шаг 1: Загружаем модель WhisperX...", file=sys.stderr)
            model = whisperx.load_model(model_size, device, compute_type=compute_type, language=language)
            print("✅ Модель WhisperX загружена", file=sys.stderr)
            
            # 2. Загружаем аудио
            print(f"🎵 Шаг 2: Загружаем аудио файл: {temp_path}", file=sys.stderr)
            audio = whisperx.load_audio(temp_path)
            print("✅ Аудио загружено", file=sys.stderr)
            
            # 3. Выполняем транскрипцию
            print("🎯 Шаг 3: Выполняем транскрипцию...", file=sys.stderr)
            result = model.transcribe(audio, batch_size=16)
            print(f"✅ Транскрипция завершена, сегментов: {len(result['segments'])}", file=sys.stderr)
            
            # 4. Выравнивание (alignment) для точной временной разметки
            print("⏰ Шаг 4: Выполняем выравнивание временных меток...", file=sys.stderr)
            try:
                model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
                result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
                print("✅ Выравнивание завершено", file=sys.stderr)
            except Exception as align_error:
                print(f"⚠️ Ошибка выравнивания: {align_error}", file=sys.stderr)
                print("📝 Продолжаем без выравнивания...", file=sys.stderr)
            
            # 5. Диаризация (разделение по говорящим)
            print("👥 Шаг 5: Выполняем диаризацию (разделение по говорящим)...", file=sys.stderr)
            diarize_segments = None
            try:
                print("🔧 Инициализируем DiarizationPipeline...", file=sys.stderr)
                diarize_model = whisperx.DiarizationPipeline(use_auth_token=None, device=device)
                print("✅ DiarizationPipeline создан", file=sys.stderr)
                
                print("🎤 Выполняем диаризацию аудио...", file=sys.stderr)
                diarize_segments = diarize_model(audio)
                print("✅ Диаризация завершена", file=sys.stderr)
                
                # 6. Назначаем говорящих к сегментам
                print("🏷️ Шаг 6: Назначаем говорящих к сегментам...", file=sys.stderr)
                try:
                    result = whisperx.assign_word_speakers(diarize_segments, result)
                    print("✅ Говорящие назначены к сегментам", file=sys.stderr)
                except Exception as assign_error:
                    print(f"⚠️ Ошибка назначения говорящих: {assign_error}", file=sys.stderr)
                    print("📝 Продолжаем без назначения говорящих...", file=sys.stderr)
                    
            except Exception as diarize_error:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ДИАРИЗАЦИИ: {diarize_error}", file=sys.stderr)
                print(f"❌ Тип ошибки: {type(diarize_error).__name__}", file=sys.stderr)
                print(f"❌ Детали ошибки: {str(diarize_error)}", file=sys.stderr)
                
                # Возвращаем ошибку для диагностики
                return {
                    'success': False,
                    'text': '',
                    'segments': [],
                    'speakers': [],
                    'speaker_count': 0,
                    'error': f'Ошибка диаризации: {str(diarize_error)}',
                    'error_type': type(diarize_error).__name__,
                    'step': 'diarization'
                }
            
            # 7. Обрабатываем результаты
            print("📊 Шаг 7: Обрабатываем результаты...", file=sys.stderr)
            if diarize_segments:
                # С диаризацией
                segments_with_speakers = []
                speakers = set()
                full_text = ""
                
                current_speaker = None
                current_text = ""
                segment_start = 0
                segment_end = 0
                
                for segment in result["segments"]:
                    speaker = segment.get("speaker", "НЕИЗВЕСТНЫЙ")
                    text = segment["text"].strip()
                    start = segment.get("start", 0)
                    end = segment.get("end", 0)
                    
                    speakers.add(speaker)
                    
                    # Группируем последовательные сегменты одного говорящего
                    if speaker == current_speaker:
                        current_text += " " + text
                        segment_end = end
                    else:
                        # Сохраняем предыдущий сегмент
                        if current_speaker is not None and current_text:
                            segments_with_speakers.append({
                                "speaker": current_speaker,
                                "text": current_text.strip(),
                                "start": segment_start,
                                "end": segment_end
                            })
                            full_text += f"\n[{current_speaker}]: {current_text.strip()}"
                        
                        # Начинаем новый сегмент
                        current_speaker = speaker
                        current_text = text
                        segment_start = start
                        segment_end = end
                
                # Добавляем последний сегмент
                if current_speaker is not None and current_text:
                    segments_with_speakers.append({
                        "speaker": current_speaker,
                        "text": current_text.strip(),
                        "start": segment_start,
                        "end": segment_end
                    })
                    full_text += f"\n[{current_speaker}]: {current_text.strip()}"
                
                full_text = full_text.strip()
                speakers_list = sorted(list(speakers))
                
                print(f"🎉 WhisperX транскрипция с диаризацией УСПЕШНО завершена!", file=sys.stderr)
                print(f"📊 Найдено говорящих: {len(speakers_list)} ({', '.join(speakers_list)})", file=sys.stderr)
                print(f"📝 Сегментов: {len(segments_with_speakers)}", file=sys.stderr)
                print(f"📄 Символов: {len(full_text)}", file=sys.stderr)
                
                return {
                    'success': True,
                    'text': full_text,
                    'segments': segments_with_speakers,
                    'speakers': speakers_list,
                    'speaker_count': len(speakers_list),
                    'language': language,
                    'error': None
                }
            else:
                # Без диаризации (fallback)
                full_text = ""
                for segment in result["segments"]:
                    full_text += segment["text"]
                
                full_text = full_text.strip()
                
                print(f"⚠️ WhisperX транскрипция БЕЗ диаризации завершена", file=sys.stderr)
                print(f"📄 Символов: {len(full_text)}", file=sys.stderr)
                
                return {
                    'success': True,
                    'text': full_text,
                    'segments': [],
                    'speakers': [],
                    'speaker_count': 0,
                    'language': language,
                    'error': None,
                    'warning': 'Диаризация не удалась, возвращен обычный текст'
                }
        
        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        error_message = str(e)
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА WhisperX: {error_message}", file=sys.stderr)
        print(f"❌ Тип ошибки: {type(e).__name__}", file=sys.stderr)
        return {
            'success': False,
            'text': '',
            'segments': [],
            'speakers': [],
            'speaker_count': 0,
            'error': error_message,
            'error_type': type(e).__name__
        }

def transcribe_audio(audio_data, language='ru', model_size='small'):
    """
    Обратная совместимость - вызывает функцию с диаризацией
    """
    return transcribe_audio_with_diarization(audio_data, language, model_size)

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
        
        # Транскрибируем с WhisperX и диаризацией
        result = transcribe_audio_with_diarization(audio_data, language, model_size)
        
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