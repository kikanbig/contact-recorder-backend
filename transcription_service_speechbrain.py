#!/usr/bin/env python3
"""
Сервис транскрипции через faster-whisper + SpeechBrain диаризация
Обрабатывает аудио файлы с разделением по говорящим
"""

import sys
import os
import json
import tempfile
import traceback

# Детальная диагностика версий библиотек
def diagnose_system():
    """Диагностика системы и версий библиотек"""
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ (SpeechBrain):", file=sys.stderr)
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
        import speechbrain
        print(f"🧠 SpeechBrain версия: {speechbrain.__version__}", file=sys.stderr)
    except ImportError as e:
        print(f"❌ SpeechBrain не найден: {e}", file=sys.stderr)
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

def diarize_with_speechbrain(audio_path, num_speakers=None):
    """Диаризация через SpeechBrain"""
    print(f"👥 Начинаем диаризацию SpeechBrain...", file=sys.stderr)
    print(f"   📁 Файл: {audio_path}", file=sys.stderr)
    print(f"   👥 Ожидаемое количество говорящих: {num_speakers or 'авто'}", file=sys.stderr)
    
    try:
        from speechbrain.pretrained import SpeakerRecognition
        import torch
        import torchaudio
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.metrics import silhouette_score
        
        # Загружаем предобученную модель для извлечения эмбеддингов
        print("📥 Загружаем модель SpeechBrain...", file=sys.stderr)
        verification = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/spkrec-ecapa-voxceleb"
        )
        
        # Загружаем аудио
        print("🎵 Загружаем аудио файл...", file=sys.stderr)
        waveform, sample_rate = torchaudio.load(audio_path)
        
        # Конвертируем в моно если нужно
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # Ресемплируем если нужно (SpeechBrain ожидает 16kHz)
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
            sample_rate = 16000
        
        print(f"   🎵 Длительность аудио: {waveform.shape[1] / sample_rate:.2f} секунд", file=sys.stderr)
        
        # Разбиваем аудио на сегменты (окна по 3 секунды с перекрытием 1.5 сек)
        window_size = 3.0  # секунды
        overlap = 1.5      # секунды
        window_samples = int(window_size * sample_rate)
        step_samples = int((window_size - overlap) * sample_rate)
        
        segments = []
        embeddings = []
        
        print("🔍 Извлекаем эмбеддинги из сегментов...", file=sys.stderr)
        
        for start_sample in range(0, waveform.shape[1] - window_samples + 1, step_samples):
            end_sample = start_sample + window_samples
            segment_waveform = waveform[:, start_sample:end_sample]
            
            start_time = start_sample / sample_rate
            end_time = end_sample / sample_rate
            
            # Извлекаем эмбеддинг
            try:
                embedding = verification.encode_batch(segment_waveform)
                embeddings.append(embedding.squeeze().cpu().numpy())
                segments.append({
                    'start': start_time,
                    'end': end_time,
                    'embedding': len(embeddings) - 1
                })
            except Exception as e:
                print(f"⚠️ Ошибка извлечения эмбеддинга для сегмента {start_time:.2f}-{end_time:.2f}: {e}", file=sys.stderr)
                continue
        
        if len(embeddings) == 0:
            print("❌ Не удалось извлечь эмбеддинги", file=sys.stderr)
            return None
        
        print(f"   📊 Извлечено эмбеддингов: {len(embeddings)}", file=sys.stderr)
        
        # Кластеризация эмбеддингов
        embeddings_array = np.array(embeddings)
        
        # Определяем оптимальное количество кластеров если не задано
        if num_speakers is None:
            print("🔍 Определяем оптимальное количество говорящих...", file=sys.stderr)
            best_score = -1
            best_n_clusters = 2
            
            for n_clusters in range(2, min(8, len(embeddings) // 2)):
                try:
                    clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
                    labels = clustering.fit_predict(embeddings_array)
                    
                    if len(set(labels)) > 1:  # Нужно минимум 2 кластера для silhouette_score
                        score = silhouette_score(embeddings_array, labels)
                        print(f"   🎯 {n_clusters} кластеров: silhouette score = {score:.3f}", file=sys.stderr)
                        
                        if score > best_score:
                            best_score = score
                            best_n_clusters = n_clusters
                except Exception as e:
                    print(f"   ⚠️ Ошибка для {n_clusters} кластеров: {e}", file=sys.stderr)
                    continue
            
            num_speakers = best_n_clusters
            print(f"   ✅ Выбрано говорящих: {num_speakers} (score: {best_score:.3f})", file=sys.stderr)
        
        # Финальная кластеризация
        print(f"🎯 Кластеризация на {num_speakers} говорящих...", file=sys.stderr)
        clustering = AgglomerativeClustering(n_clusters=num_speakers, linkage='ward')
        labels = clustering.fit_predict(embeddings_array)
        
        # Присваиваем метки сегментам
        diarization_segments = []
        speakers = set()
        
        for i, segment in enumerate(segments):
            speaker_id = f"SPEAKER_{labels[i]:02d}"
            diarization_segments.append({
                'start': segment['start'],
                'end': segment['end'],
                'speaker': speaker_id
            })
            speakers.add(speaker_id)
        
        # Объединяем соседние сегменты одного говорящего
        merged_segments = []
        current_segment = None
        
        for segment in sorted(diarization_segments, key=lambda x: x['start']):
            if current_segment is None or current_segment['speaker'] != segment['speaker']:
                if current_segment:
                    merged_segments.append(current_segment)
                current_segment = segment.copy()
            else:
                current_segment['end'] = segment['end']
        
        if current_segment:
            merged_segments.append(current_segment)
        
        print(f"✅ SpeechBrain диаризация завершена", file=sys.stderr)
        print(f"   👥 Найдено говорящих: {len(speakers)}", file=sys.stderr)
        print(f"   🎯 Сегментов диаризации: {len(merged_segments)}", file=sys.stderr)
        
        return {
            'segments': merged_segments,
            'speakers': list(speakers),
            'speaker_count': len(speakers)
        }
        
    except Exception as e:
        print(f"❌ Ошибка SpeechBrain диаризации: {e}", file=sys.stderr)
        print(f"❌ Traceback: {traceback.format_exc()}", file=sys.stderr)
        return None

def combine_transcription_and_diarization(whisper_result, speechbrain_result):
    """Объединение результатов транскрипции и диаризации"""
    print("🔗 Объединяем транскрипцию и диаризацию...", file=sys.stderr)
    
    if not whisper_result or not speechbrain_result:
        print("❌ Отсутствуют данные для объединения", file=sys.stderr)
        return None
    
    whisper_segments = whisper_result['segments']
    diarization_segments = speechbrain_result['segments']
    
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
        'speaker_count': speechbrain_result['speaker_count'],
        'speakers': speechbrain_result['speakers'],
        'language': whisper_result['language'],
        'language_probability': whisper_result['language_probability']
    }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Использование: python transcription_service_speechbrain.py <audio_file> [language] [model_size] [num_speakers]"
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
        
        # Шаг 2: Диаризация через SpeechBrain
        print("=" * 50, file=sys.stderr)
        print("🧠 ШАГ 2: ДИАРИЗАЦИЯ SPEECHBRAIN", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        speechbrain_result = diarize_with_speechbrain(audio_file, num_speakers)
        if not speechbrain_result:
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
        
        final_result = combine_transcription_and_diarization(whisper_result, speechbrain_result)
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