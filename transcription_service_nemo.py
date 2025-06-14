#!/usr/bin/env python3
"""
Сервис транскрипции через faster-whisper + NVIDIA NeMo диаризация
Обрабатывает аудио файлы с разделением по говорящим
"""

import sys
import os
import json
import tempfile
import traceback
import subprocess

# Детальная диагностика версий библиотек
def diagnose_system():
    """Диагностика системы и версий библиотек"""
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ (NeMo):", file=sys.stderr)
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
        print(f"🎤 faster-whisper версия: {faster_whisper.__version__}", file=sys.stderr)
    except ImportError as e:
        print(f"❌ faster-whisper не найден: {e}", file=sys.stderr)
        return False
    
    try:
        import nemo
        print(f"🤖 NeMo версия: {nemo.__version__}", file=sys.stderr)
    except ImportError as e:
        print(f"❌ NeMo не найден: {e}", file=sys.stderr)
        return False
    
    try:
        import librosa
        print(f"🎵 librosa версия: {librosa.__version__}", file=sys.stderr)
    except ImportError as e:
        print(f"❌ librosa не найден: {e}", file=sys.stderr)
        return False
    
    print("✅ Все основные библиотеки найдены", file=sys.stderr)
    return True

def transcribe_with_whisper(audio_path, language='ru', model_size='small'):
    """Транскрипция через faster-whisper"""
    print(f"🎤 Начинаем транскрипцию Whisper...", file=sys.stderr)
    print(f"   📁 Файл: {audio_path}", file=sys.stderr)
    print(f"   🌍 Язык: {language}", file=sys.stderr)
    print(f"   🤖 Модель: {model_size}", file=sys.stderr)
    
    try:
        from faster_whisper import WhisperModel
        
        # Загружаем модель
        print(f"📥 Загружаем модель Whisper {model_size}...", file=sys.stderr)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        # Транскрибируем
        print("🚀 Запускаем транскрипцию...", file=sys.stderr)
        segments, info = model.transcribe(
            audio_path, 
            language=language,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # Собираем результаты
        whisper_segments = []
        full_text = ""
        
        for segment in segments:
            segment_text = segment.text.strip()
            if segment_text:
                whisper_segments.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment_text,
                    'words': [
                        {
                            'word': word.word,
                            'start': word.start,
                            'end': word.end,
                            'probability': word.probability
                        } for word in segment.words
                    ] if segment.words else []
                })
                full_text += segment_text + " "
        
        print(f"✅ Whisper транскрипция завершена", file=sys.stderr)
        print(f"   📝 Сегментов: {len(whisper_segments)}", file=sys.stderr)
        print(f"   📏 Длина текста: {len(full_text)} символов", file=sys.stderr)
        
        return {
            'text': full_text.strip(),
            'segments': whisper_segments,
            'language': info.language,
            'language_probability': info.language_probability
        }
        
    except Exception as e:
        print(f"❌ Ошибка Whisper транскрипции: {e}", file=sys.stderr)
        print(f"❌ Traceback: {traceback.format_exc()}", file=sys.stderr)
        return None

def diarize_with_nemo(audio_path, num_speakers=None):
    """Диаризация через NVIDIA NeMo"""
    print(f"👥 Начинаем диаризацию NeMo...", file=sys.stderr)
    print(f"   📁 Файл: {audio_path}", file=sys.stderr)
    print(f"   👥 Ожидаемое количество говорящих: {num_speakers or 'авто'}", file=sys.stderr)
    
    try:
        from nemo.collections.asr.models import ClusteringDiarizer
        from omegaconf import OmegaConf
        import tempfile
        import json
        
        # Создаем временные файлы для NeMo
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"📂 Временная директория: {temp_dir}", file=sys.stderr)
            
            # Создаем манифест файл
            manifest_path = os.path.join(temp_dir, 'input_manifest.json')
            manifest_data = {
                'audio_filepath': audio_path,
                'offset': 0,
                'duration': None,
                'label': 'infer',
                'text': '-',
                'num_speakers': num_speakers,
                'rttm_filepath': None,
                'uem_filepath': None
            }
            
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f)
                f.write('\n')
            
            print(f"📄 Манифест создан: {manifest_path}", file=sys.stderr)
            
            # Конфигурация NeMo
            config = {
                'diarizer': {
                    'manifest_filepath': manifest_path,
                    'out_dir': temp_dir,
                    'oracle_vad': False,
                    'clustering': {
                        'parameters': {
                            'oracle_num_speakers': False,
                            'max_num_speakers': 8,
                            'enhanced_count_thres': 0.80,
                            'maj_vote_spk_count': False,
                        }
                    },
                    'speaker_embeddings': {
                        'model_path': 'titanet_large',
                        'parameters': {
                            'window_length_in_sec': 1.5,
                            'shift_length_in_sec': 0.75,
                            'multiscale_weights': [1, 1, 1],
                            'multiscale_args_dict': {
                                'scale_dict': [
                                    {'window_length_in_sec': 1.5, 'shift_length_in_sec': 0.75},
                                    {'window_length_in_sec': 1.0, 'shift_length_in_sec': 0.5},
                                    {'window_length_in_sec': 0.5, 'shift_length_in_sec': 0.25}
                                ]
                            }
                        }
                    },
                    'vad': {
                        'model_path': 'vad_multilingual_marblenet',
                        'parameters': {
                            'window_length_in_sec': 0.15,
                            'shift_length_in_sec': 0.01,
                            'smoothing': 'median',
                            'overlap': 0.875,
                            'onset': 0.4,
                            'offset': 0.7,
                            'pad_onset': 0.05,
                            'pad_offset': -0.1,
                            'min_duration_on': 0.2,
                            'min_duration_off': 0.2
                        }
                    }
                }
            }
            
            if num_speakers:
                config['diarizer']['clustering']['parameters']['oracle_num_speakers'] = True
                config['diarizer']['clustering']['parameters']['max_num_speakers'] = num_speakers
            
            # Создаем конфигурационный файл
            config_path = os.path.join(temp_dir, 'config.yaml')
            cfg = OmegaConf.create(config)
            OmegaConf.save(cfg, config_path)
            
            print(f"⚙️ Конфигурация создана: {config_path}", file=sys.stderr)
            
            # Запускаем диаризацию
            print("🚀 Запускаем NeMo диаризацию...", file=sys.stderr)
            sd_model = ClusteringDiarizer(cfg=cfg.diarizer)
            sd_model.diarize()
            
            # Читаем результаты
            rttm_path = os.path.join(temp_dir, 'pred_rttms', os.path.basename(audio_path).replace('.wav', '.rttm'))
            if not os.path.exists(rttm_path):
                # Пробуем другие возможные пути
                for file in os.listdir(os.path.join(temp_dir, 'pred_rttms')):
                    if file.endswith('.rttm'):
                        rttm_path = os.path.join(temp_dir, 'pred_rttms', file)
                        break
            
            if not os.path.exists(rttm_path):
                print(f"❌ RTTM файл не найден: {rttm_path}", file=sys.stderr)
                return None
            
            print(f"📄 Читаем RTTM файл: {rttm_path}", file=sys.stderr)
            
            # Парсим RTTM файл
            diarization_segments = []
            speakers = set()
            
            with open(rttm_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 8:
                        start_time = float(parts[3])
                        duration = float(parts[4])
                        end_time = start_time + duration
                        speaker = parts[7]
                        
                        diarization_segments.append({
                            'start': start_time,
                            'end': end_time,
                            'speaker': speaker
                        })
                        speakers.add(speaker)
            
            print(f"✅ NeMo диаризация завершена", file=sys.stderr)
            print(f"   👥 Найдено говорящих: {len(speakers)}", file=sys.stderr)
            print(f"   🎯 Сегментов диаризации: {len(diarization_segments)}", file=sys.stderr)
            
            return {
                'segments': diarization_segments,
                'speakers': list(speakers),
                'speaker_count': len(speakers)
            }
            
    except Exception as e:
        print(f"❌ Ошибка NeMo диаризации: {e}", file=sys.stderr)
        print(f"❌ Traceback: {traceback.format_exc()}", file=sys.stderr)
        return None

def combine_transcription_and_diarization(whisper_result, nemo_result):
    """Объединение результатов транскрипции и диаризации"""
    print("🔗 Объединяем транскрипцию и диаризацию...", file=sys.stderr)
    
    if not whisper_result or not nemo_result:
        print("❌ Отсутствуют данные для объединения", file=sys.stderr)
        return None
    
    whisper_segments = whisper_result['segments']
    diarization_segments = nemo_result['segments']
    
    combined_segments = []
    
    for w_seg in whisper_segments:
        w_start, w_end = w_seg['start'], w_seg['end']
        w_text = w_seg['text']
        
        # Находим наиболее подходящий сегмент диаризации
        best_speaker = "SPEAKER_00"  # По умолчанию
        max_overlap = 0
        
        for d_seg in diarization_segments:
            d_start, d_end = d_seg['start'], d_seg['end']
            
            # Вычисляем пересечение
            overlap_start = max(w_start, d_start)
            overlap_end = min(w_end, d_end)
            overlap_duration = max(0, overlap_end - overlap_start)
            
            if overlap_duration > max_overlap:
                max_overlap = overlap_duration
                best_speaker = d_seg['speaker']
        
        combined_segments.append({
            'start': w_start,
            'end': w_end,
            'text': w_text,
            'speaker': best_speaker,
            'words': w_seg.get('words', [])
        })
    
    # Группируем соседние сегменты одного говорящего
    grouped_segments = []
    current_group = None
    
    for segment in combined_segments:
        if current_group is None or current_group['speaker'] != segment['speaker']:
            if current_group:
                grouped_segments.append(current_group)
            current_group = {
                'start': segment['start'],
                'end': segment['end'],
                'text': segment['text'],
                'speaker': segment['speaker']
            }
        else:
            current_group['end'] = segment['end']
            current_group['text'] += ' ' + segment['text']
    
    if current_group:
        grouped_segments.append(current_group)
    
    print(f"✅ Объединение завершено", file=sys.stderr)
    print(f"   🎯 Итоговых сегментов: {len(grouped_segments)}", file=sys.stderr)
    
    return {
        'text': whisper_result['text'],
        'segments': grouped_segments,
        'speaker_count': nemo_result['speaker_count'],
        'speakers': nemo_result['speakers'],
        'language': whisper_result['language'],
        'language_probability': whisper_result['language_probability']
    }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Использование: python transcription_service_nemo.py <audio_file> [language] [model_size] [num_speakers]"
        }))
        sys.exit(1)
    
    audio_file = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else 'ru'
    model_size = sys.argv[3] if len(sys.argv) > 3 else 'small'
    num_speakers = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else None
    
    print(f"🎯 Параметры обработки:", file=sys.stderr)
    print(f"   📁 Аудио файл: {audio_file}", file=sys.stderr)
    print(f"   🌍 Язык: {language}", file=sys.stderr)
    print(f"   🤖 Модель Whisper: {model_size}", file=sys.stderr)
    print(f"   👥 Количество говорящих: {num_speakers or 'авто'}", file=sys.stderr)
    
    # Проверяем существование файла
    if not os.path.exists(audio_file):
        print(json.dumps({
            "success": False,
            "error": f"Аудио файл не найден: {audio_file}"
        }))
        sys.exit(1)
    
    # Диагностика системы
    if not diagnose_system():
        print(json.dumps({
            "success": False,
            "error": "Системная диагностика не пройдена - отсутствуют необходимые библиотеки"
        }))
        sys.exit(1)
    
    try:
        # Шаг 1: Транскрипция через Whisper
        print("=" * 50, file=sys.stderr)
        print("🎤 ШАГ 1: ТРАНСКРИПЦИЯ WHISPER", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        whisper_result = transcribe_with_whisper(audio_file, language, model_size)
        if not whisper_result:
            print(json.dumps({
                "success": False,
                "error": "Ошибка транскрипции Whisper"
            }))
            sys.exit(1)
        
        # Шаг 2: Диаризация через NeMo
        print("=" * 50, file=sys.stderr)
        print("👥 ШАГ 2: ДИАРИЗАЦИЯ NEMO", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        nemo_result = diarize_with_nemo(audio_file, num_speakers)
        if not nemo_result:
            # Fallback: возвращаем результат без диаризации
            print("⚠️ Диаризация не удалась, возвращаем результат без разделения говорящих", file=sys.stderr)
            print(json.dumps({
                "success": True,
                "text": whisper_result['text'],
                "segments": [{
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text'],
                    'speaker': 'SPEAKER_00'
                } for seg in whisper_result['segments']],
                "speaker_count": 1,
                "speakers": ["SPEAKER_00"],
                "language": whisper_result['language'],
                "language_probability": whisper_result['language_probability'],
                "warning": "Диаризация не удалась, все сегменты приписаны одному говорящему"
            }))
            sys.exit(0)
        
        # Шаг 3: Объединение результатов
        print("=" * 50, file=sys.stderr)
        print("🔗 ШАГ 3: ОБЪЕДИНЕНИЕ РЕЗУЛЬТАТОВ", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        final_result = combine_transcription_and_diarization(whisper_result, nemo_result)
        if not final_result:
            print(json.dumps({
                "success": False,
                "error": "Ошибка объединения результатов"
            }))
            sys.exit(1)
        
        # Возвращаем финальный результат
        print("✅ Обработка завершена успешно!", file=sys.stderr)
        print(json.dumps({
            "success": True,
            **final_result
        }))
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}", file=sys.stderr)
        print(f"❌ Traceback: {traceback.format_exc()}", file=sys.stderr)
        print(json.dumps({
            "success": False,
            "error": f"Критическая ошибка обработки: {str(e)}"
        }))
        sys.exit(1)

if __name__ == "__main__":
    main() 