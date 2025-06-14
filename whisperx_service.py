#!/usr/bin/env python3
"""
Сверхбыстрый сервис транскрипции через WhisperX с диаризацией спикеров
Разделяет голоса покупателя и клиента, ускорение до 70x
"""

import sys
import os
import json
import tempfile
import warnings
from pathlib import Path

# Подавляем предупреждения для чистого вывода
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    import whisperx
    import torch
except ImportError as e:
    print(json.dumps({
        'success': False,
        'error': f'Не установлены зависимости WhisperX: {str(e)}'
    }, ensure_ascii=False))
    sys.exit(1)

def format_dialogue(segments, speakers_info):
    """
    Форматирует сегменты в диалог с указанием спикеров
    
    Args:
        segments: Список сегментов с информацией о спикерах
        speakers_info: Информация о спикерах
    
    Returns:
        str: Отформатированный диалог
    """
    if not segments or not speakers_info:
        return ""
    
    dialogue_lines = []
    current_speaker = None
    current_text = ""
    
    # Определяем роли спикеров
    seller_id = speakers_info.get("seller")
    client_id = speakers_info.get("client")
    
    for segment in segments:
        speaker = segment.get("speaker")
        text = segment.get("text", "").strip()
        
        if not text:
            continue
            
        # Определяем роль спикера
        if speaker == seller_id:
            speaker_role = "Продавец"
        elif speaker == client_id:
            speaker_role = "Клиент"
        elif speaker:
            speaker_role = f"Спикер {speaker}"
        else:
            speaker_role = "Неизвестный"
        
        # Если спикер сменился, сохраняем предыдущую реплику
        if current_speaker and current_speaker != speaker_role and current_text:
            dialogue_lines.append(f"{current_speaker}: {current_text.strip()}")
            current_text = ""
        
        # Обновляем текущего спикера и добавляем текст
        current_speaker = speaker_role
        current_text += " " + text
    
    # Добавляем последнюю реплику
    if current_speaker and current_text:
        dialogue_lines.append(f"{current_speaker}: {current_text.strip()}")
    
    return "\n\n".join(dialogue_lines)

def transcribe_with_speaker_diarization(audio_data, language='ru', model_size='small', hf_token=None):
    """
    Транскрибирует аудио с разделением спикеров через WhisperX
    
    Args:
        audio_data: Бинарные данные аудио файла
        language: Язык для транскрипции (по умолчанию 'ru')
        model_size: Размер модели ('tiny', 'base', 'small', 'medium', 'large')
        hf_token: HuggingFace токен для диаризации (опционально)
    
    Returns:
        dict: {
            'success': bool,
            'text': str,
            'speakers': dict,
            'segments': list,
            'error': str
        }
    """
    try:
        print(f"🚀 Загружаем WhisperX модель: {model_size}", file=sys.stderr)
        
        # Определяем устройство (CPU/GPU)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        print(f"💻 Устройство: {device}, тип вычислений: {compute_type}", file=sys.stderr)
        
        # Создаем временный файл для аудио
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            # 1. Загружаем модель WhisperX
            model = whisperx.load_model(
                model_size, 
                device=device, 
                compute_type=compute_type,
                language=language
            )
            
            print(f"✅ WhisperX модель {model_size} загружена", file=sys.stderr)
            
            # 2. Транскрибируем с батчингом (основное ускорение)
            print(f"🎵 Транскрибируем с батчингом...", file=sys.stderr)
            
            audio = whisperx.load_audio(temp_path)
            result = model.transcribe(
                audio, 
                batch_size=16,  # Батчинг для ускорения до 70x
                language=language
            )
            
            print(f"⚡ Базовая транскрипция завершена", file=sys.stderr)
            
            # 3. Выравнивание слов (word-level alignment)
            print(f"🎯 Выравнивание слов...", file=sys.stderr)
            
            model_a, metadata = whisperx.load_align_model(
                language_code=language, 
                device=device
            )
            
            result = whisperx.align(
                result["segments"], 
                model_a, 
                metadata, 
                audio, 
                device, 
                return_char_alignments=False
            )
            
            print(f"✅ Выравнивание слов завершено", file=sys.stderr)
            
            # 4. Диаризация спикеров (разделение голосов)
            speakers_info = {}
            segments_with_speakers = result["segments"]
            
            try:
                if hf_token:
                    print(f"👥 Диаризация спикеров с HF токеном...", file=sys.stderr)
                    
                    diarize_model = whisperx.DiarizationPipeline(
                        use_auth_token=hf_token, 
                        device=device
                    )
                    
                    diarize_segments = diarize_model(audio)
                    result = whisperx.assign_word_speakers(diarize_segments, result)
                    
                    # Анализируем спикеров
                    speakers = set()
                    for segment in result["segments"]:
                        if "speaker" in segment:
                            speakers.add(segment["speaker"])
                    
                    speakers_list = sorted(list(speakers))
                    
                    # Предполагаем: первый спикер = продавец, второй = клиент
                    if len(speakers_list) >= 2:
                        speakers_info = {
                            "seller": speakers_list[0],
                            "client": speakers_list[1],
                            "total_speakers": len(speakers_list),
                            "all_speakers": speakers_list
                        }
                    elif len(speakers_list) == 1:
                        speakers_info = {
                            "seller": speakers_list[0],
                            "client": None,
                            "total_speakers": 1,
                            "all_speakers": speakers_list,
                            "note": "Обнаружен только один спикер"
                        }
                    
                    segments_with_speakers = result["segments"]
                    print(f"✅ Диаризация завершена: {len(speakers_list)} спикеров", file=sys.stderr)
                    
                else:
                    print(f"⚠️ Диаризация пропущена: нет HF токена", file=sys.stderr)
                    speakers_info = {
                        "note": "Диаризация недоступна без HuggingFace токена"
                    }
                    
            except Exception as diarize_error:
                print(f"⚠️ Ошибка диаризации: {str(diarize_error)}", file=sys.stderr)
                speakers_info = {
                    "error": f"Диаризация не удалась: {str(diarize_error)}"
                }
            
            # 5. Собираем результат
            full_text = ""
            seller_text = ""
            client_text = ""
            
            for segment in segments_with_speakers:
                text = segment.get("text", "").strip()
                full_text += text + " "
                
                speaker = segment.get("speaker")
                if speaker == speakers_info.get("seller"):
                    seller_text += text + " "
                elif speaker == speakers_info.get("client"):
                    client_text += text + " "
            
            full_text = full_text.strip()
            seller_text = seller_text.strip()
            client_text = client_text.strip()
            
            # 6. Создаём диалог в формате "Продавец: ... Клиент: ..."
            dialogue_text = format_dialogue(segments_with_speakers, speakers_info)
            
            print(f"✅ WhisperX транскрипция завершена: {len(full_text)} символов", file=sys.stderr)
            print(f"👤 Продавец: {len(seller_text)} символов", file=sys.stderr)
            print(f"🛒 Клиент: {len(client_text)} символов", file=sys.stderr)
            print(f"💬 Диалог: {len(dialogue_text)} символов", file=sys.stderr)
            
            return {
                'success': True,
                'text': full_text,
                'dialogue': dialogue_text,
                'seller_text': seller_text,
                'client_text': client_text,
                'speakers': speakers_info,
                'segments': segments_with_speakers,
                'language': language,
                'model_used': f'whisperx-{model_size}',
                'device': device,
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
            'dialogue': '',
            'seller_text': '',
            'client_text': '',
            'speakers': {},
            'segments': [],
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
    hf_token = sys.argv[4] if len(sys.argv) > 4 else None
    
    try:
        print(f"📂 Читаем аудио файл: {audio_file_path}", file=sys.stderr)
        
        # Читаем аудио файл
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        
        print(f"📦 Размер аудио файла: {len(audio_data)} байт", file=sys.stderr)
        
        # Транскрибируем с WhisperX и диаризацией
        result = transcribe_with_speaker_diarization(audio_data, language, model_size, hf_token)
        
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