#!/usr/bin/env python3
"""
УЛУЧШЕННЫЙ сервис транскрипции с продвинутой диаризацией на основе тембра голоса
Версия 3.3.0 - Enhanced Voice Timbre Analysis
"""

import sys
import os
import json
import tempfile
import traceback
import numpy as np
from typing import List, Dict, Tuple, Optional

def diagnose_system():
    """Диагностика системы и версий библиотек"""
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ (Enhanced):", file=sys.stderr)
    print(f"🐍 Python версия: {sys.version}", file=sys.stderr)
    
    required_libs = [
        ('torch', 'PyTorch'),
        ('faster_whisper', 'faster-whisper'),
        ('speechbrain', 'SpeechBrain'),
        ('librosa', 'librosa'),
        ('sklearn', 'scikit-learn'),
        ('scipy', 'SciPy'),
        ('numpy', 'NumPy')
    ]
    
    for lib_name, display_name in required_libs:
        try:
            lib = __import__(lib_name)
            version = getattr(lib, '__version__', 'unknown')
            print(f"✅ {display_name}: {version}", file=sys.stderr)
        except ImportError as e:
            print(f"❌ {display_name} не найден: {e}", file=sys.stderr)
            return False
    
    print("✅ Все библиотеки найдены", file=sys.stderr)
    return True

class EnhancedVoiceAnalyzer:
    """Улучшенный анализатор голосовых характеристик"""
    
    def __init__(self):
        self.sample_rate = 16000
        self.verification_model = None
        self.vad_model = None
        
    def load_models(self):
        """Загрузка моделей"""
        print("📥 Загружаем улучшенные модели...", file=sys.stderr)
        
        try:
            from speechbrain.pretrained import SpeakerRecognition
            # Используем более современную модель
            self.verification_model = SpeakerRecognition.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="pretrained_models/spkrec-ecapa-voxceleb"
            )
            print("✅ Модель распознавания говорящих загружена", file=sys.stderr)
            
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}", file=sys.stderr)
            raise
    
    def extract_voice_features(self, waveform: np.ndarray, start_time: float, end_time: float) -> Dict:
        """Извлечение расширенных голосовых характеристик"""
        import librosa
        
        # 1. Эмбеддинг говорящего (основная характеристика)
        try:
            import torch
            waveform_tensor = torch.FloatTensor(waveform).unsqueeze(0)
            speaker_embedding = self.verification_model.encode_batch(waveform_tensor)
            speaker_embedding = speaker_embedding.squeeze().cpu().numpy()
        except Exception as e:
            print(f"⚠️ Ошибка извлечения эмбеддинга: {e}", file=sys.stderr)
            speaker_embedding = np.zeros(192)  # Fallback
        
        # 2. Основная частота (F0) - высота голоса
        try:
            f0, voiced_flag, voiced_probs = librosa.pyin(
                waveform, 
                fmin=librosa.note_to_hz('C2'), 
                fmax=librosa.note_to_hz('C7'),
                sr=self.sample_rate
            )
            f0_mean = np.nanmean(f0[voiced_flag])
            f0_std = np.nanstd(f0[voiced_flag])
            f0_range = np.nanmax(f0[voiced_flag]) - np.nanmin(f0[voiced_flag])
        except:
            f0_mean = f0_std = f0_range = 0
        
        # 3. Спектральные характеристики
        try:
            # Спектральный центроид (яркость звука)
            spectral_centroids = librosa.feature.spectral_centroid(y=waveform, sr=self.sample_rate)[0]
            spectral_centroid_mean = np.mean(spectral_centroids)
            
            # Спектральная полоса пропускания
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=waveform, sr=self.sample_rate)[0]
            spectral_bandwidth_mean = np.mean(spectral_bandwidth)
            
            # Спектральный контраст
            spectral_contrast = librosa.feature.spectral_contrast(y=waveform, sr=self.sample_rate)
            spectral_contrast_mean = np.mean(spectral_contrast, axis=1)
            
            # MFCC коэффициенты
            mfccs = librosa.feature.mfcc(y=waveform, sr=self.sample_rate, n_mfcc=13)
            mfcc_mean = np.mean(mfccs, axis=1)
            mfcc_std = np.std(mfccs, axis=1)
            
        except Exception as e:
            print(f"⚠️ Ошибка спектрального анализа: {e}", file=sys.stderr)
            spectral_centroid_mean = spectral_bandwidth_mean = 0
            spectral_contrast_mean = np.zeros(7)
            mfcc_mean = mfcc_std = np.zeros(13)
        
        # 4. Темпоральные характеристики
        try:
            # Темп речи (приблизительно)
            onset_frames = librosa.onset.onset_detect(y=waveform, sr=self.sample_rate)
            speech_rate = len(onset_frames) / (len(waveform) / self.sample_rate)
            
            # Энергия сигнала
            rms_energy = librosa.feature.rms(y=waveform)[0]
            energy_mean = np.mean(rms_energy)
            energy_std = np.std(rms_energy)
            
        except:
            speech_rate = energy_mean = energy_std = 0
        
        # Объединяем все характеристики в один вектор
        voice_features = np.concatenate([
            speaker_embedding,  # 192 измерения
            [f0_mean, f0_std, f0_range],  # 3 измерения F0
            [spectral_centroid_mean, spectral_bandwidth_mean],  # 2 измерения спектра
            spectral_contrast_mean,  # 7 измерений контраста
            mfcc_mean,  # 13 измерений MFCC средние
            mfcc_std,   # 13 измерений MFCC стандартные отклонения
            [speech_rate, energy_mean, energy_std]  # 3 измерения темпоральных характеристик
        ])
        
        return {
            'features': voice_features,
            'f0_mean': f0_mean,
            'f0_std': f0_std,
            'f0_range': f0_range,
            'spectral_centroid': spectral_centroid_mean,
            'spectral_bandwidth': spectral_bandwidth_mean,
            'speech_rate': speech_rate,
            'energy_mean': energy_mean,
            'start_time': start_time,
            'end_time': end_time
        }
    
    def adaptive_segmentation(self, waveform: np.ndarray) -> List[Tuple[float, float]]:
        """Адаптивная сегментация на основе VAD"""
        import librosa
        
        print("🎯 Адаптивная сегментация аудио...", file=sys.stderr)
        
        try:
            # Простой VAD на основе энергии
            frame_length = int(0.025 * self.sample_rate)  # 25ms
            hop_length = int(0.010 * self.sample_rate)    # 10ms
            
            # RMS энергия
            rms = librosa.feature.rms(
                y=waveform, 
                frame_length=frame_length, 
                hop_length=hop_length
            )[0]
            
            # Определяем порог активности
            rms_threshold = np.percentile(rms, 30)  # 30-й процентиль как порог
            
            # Находим активные сегменты
            active_frames = rms > rms_threshold
            
            # Группируем соседние активные фреймы
            segments = []
            start_frame = None
            
            for i, is_active in enumerate(active_frames):
                if is_active and start_frame is None:
                    start_frame = i
                elif not is_active and start_frame is not None:
                    # Конец активного сегмента
                    start_time = start_frame * hop_length / self.sample_rate
                    end_time = i * hop_length / self.sample_rate
                    
                    # Добавляем сегмент только если он достаточно длинный
                    if end_time - start_time >= 1.0:  # Минимум 1 секунда
                        segments.append((start_time, end_time))
                    
                    start_frame = None
            
            # Закрываем последний сегмент если нужно
            if start_frame is not None:
                start_time = start_frame * hop_length / self.sample_rate
                end_time = len(waveform) / self.sample_rate
                if end_time - start_time >= 1.0:
                    segments.append((start_time, end_time))
            
            # Если сегментов слишком мало, используем фиксированные окна
            if len(segments) < 3:
                print("⚠️ Мало VAD сегментов, используем фиксированные окна", file=sys.stderr)
                segments = []
                window_size = 3.0
                overlap = 1.0
                
                duration = len(waveform) / self.sample_rate
                for start in np.arange(0, duration - window_size + 0.1, window_size - overlap):
                    end = min(start + window_size, duration)
                    segments.append((start, end))
            
            print(f"✅ Создано сегментов: {len(segments)}", file=sys.stderr)
            return segments
            
        except Exception as e:
            print(f"❌ Ошибка адаптивной сегментации: {e}", file=sys.stderr)
            # Fallback к фиксированным окнам
            duration = len(waveform) / self.sample_rate
            segments = []
            for start in np.arange(0, duration, 2.0):
                end = min(start + 3.0, duration)
                segments.append((start, end))
            return segments

    def fine_grained_voice_analysis(self, waveform: np.ndarray) -> List[Dict]:
        """Детальный анализ голосовых характеристик с высокой частотой"""
        import librosa
        
        print("🔬 Детальный анализ голосовых характеристик (каждые 200ms)...", file=sys.stderr)
        
        # Анализируем каждые 200ms с перекрытием 100ms
        window_size = 0.2  # 200ms
        hop_size = 0.1     # 100ms (50% перекрытие)
        
        duration = len(waveform) / self.sample_rate
        voice_analysis = []
        
        for start_time in np.arange(0, duration - window_size + 0.01, hop_size):
            end_time = min(start_time + window_size, duration)
            
            start_sample = int(start_time * self.sample_rate)
            end_sample = int(end_time * self.sample_rate)
            segment_waveform = waveform[start_sample:end_sample]
            
            if len(segment_waveform) < self.sample_rate * 0.1:  # Минимум 100ms
                continue
                
            try:
                # Быстрый анализ ключевых характеристик
                features = self.extract_compact_voice_features(segment_waveform, start_time, end_time)
                if features is not None:
                    voice_analysis.append(features)
            except Exception as e:
                continue
        
        print(f"✅ Проанализировано микро-сегментов: {len(voice_analysis)}", file=sys.stderr)
        return voice_analysis
    
    def extract_compact_voice_features(self, waveform: np.ndarray, start_time: float, end_time: float) -> Dict:
        """Быстрое извлечение ключевых голосовых характеристик"""
        import librosa
        
        try:
            # 1. SpeechBrain эмбеддинг (основа)
            waveform_tensor = torch.tensor(waveform).unsqueeze(0)
            with torch.no_grad():
                speaker_embedding = self.verification_model.encode_batch(waveform_tensor).squeeze().numpy()
            
            # 2. F0 (основная частота) - ключевая характеристика тембра
            f0, voiced_flag, voiced_probs = librosa.pyin(
                waveform, 
                fmin=librosa.note_to_hz('C2'), 
                fmax=librosa.note_to_hz('C7'),
                sr=self.sample_rate
            )
            
            # Фильтруем только уверенные F0 значения
            confident_f0 = f0[voiced_probs > 0.7]
            if len(confident_f0) > 0:
                f0_mean = np.nanmean(confident_f0)
                f0_std = np.nanstd(confident_f0)
                f0_range = np.nanmax(confident_f0) - np.nanmin(confident_f0)
            else:
                f0_mean = f0_std = f0_range = 0
            
            # 3. Спектральный центроид (яркость голоса)
            spectral_centroid = librosa.feature.spectral_centroid(y=waveform, sr=self.sample_rate)[0]
            centroid_mean = np.mean(spectral_centroid)
            
            # 4. Формантные характеристики (упрощенные)
            mfcc = librosa.feature.mfcc(y=waveform, sr=self.sample_rate, n_mfcc=5)  # Только первые 5
            mfcc_mean = np.mean(mfcc, axis=1)
            
            # 5. Энергия и динамика
            rms_energy = librosa.feature.rms(y=waveform)[0]
            energy_mean = np.mean(rms_energy)
            
            # Компактный вектор признаков (202 измерения)
            compact_features = np.concatenate([
                speaker_embedding,  # 192 измерения
                [f0_mean, f0_std, f0_range],  # 3 измерения F0
                [centroid_mean],  # 1 измерение спектра
                mfcc_mean,  # 5 измерений MFCC
                [energy_mean]  # 1 измерение энергии
            ])
            
            return {
                'features': compact_features,
                'start_time': start_time,
                'end_time': end_time,
                'f0_mean': f0_mean,
                'f0_std': f0_std,
                'spectral_centroid': centroid_mean,
                'energy': energy_mean,
                'confidence': np.mean(voiced_probs) if len(voiced_probs) > 0 else 0
            }
            
        except Exception as e:
            return None

def enhanced_clustering(features_list: List[np.ndarray], num_speakers: Optional[int] = None) -> np.ndarray:
    """Улучшенная кластеризация с несколькими алгоритмами"""
    from sklearn.cluster import AgglomerativeClustering, DBSCAN, SpectralClustering
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler
    
    print("🎯 Улучшенная кластеризация голосов...", file=sys.stderr)
    
    if len(features_list) < 2:
        return np.array([0] * len(features_list))
    
    # Нормализация признаков
    scaler = StandardScaler()
    features_array = np.array(features_list)
    features_normalized = scaler.fit_transform(features_array)
    
    best_labels = None
    best_score = -1
    best_method = "unknown"
    
    # Определяем диапазон количества кластеров
    if num_speakers is None:
        min_clusters = 2
        max_clusters = min(8, len(features_list) // 3)
    else:
        min_clusters = max_clusters = num_speakers
    
    # Пробуем разные алгоритмы кластеризации
    clustering_methods = [
        ('Agglomerative-ward', lambda n: AgglomerativeClustering(n_clusters=n, linkage='ward')),
        ('Agglomerative-complete', lambda n: AgglomerativeClustering(n_clusters=n, linkage='complete')),
        ('Spectral', lambda n: SpectralClustering(n_clusters=n, random_state=42)),
    ]
    
    for method_name, method_func in clustering_methods:
        for n_clusters in range(min_clusters, max_clusters + 1):
            try:
                clustering = method_func(n_clusters)
                labels = clustering.fit_predict(features_normalized)
                
                if len(set(labels)) > 1:
                    score = silhouette_score(features_normalized, labels)
                    print(f"   🎯 {method_name} ({n_clusters} кластеров): score = {score:.3f}", file=sys.stderr)
                    
                    if score > best_score:
                        best_score = score
                        best_labels = labels
                        best_method = f"{method_name}-{n_clusters}"
                        
            except Exception as e:
                print(f"   ⚠️ Ошибка {method_name} ({n_clusters}): {e}", file=sys.stderr)
                continue
    
    # Fallback если ничего не сработало
    if best_labels is None:
        print("⚠️ Используем простую кластеризацию", file=sys.stderr)
        clustering = AgglomerativeClustering(n_clusters=2, linkage='ward')
        best_labels = clustering.fit_predict(features_normalized)
        best_method = "fallback"
    
    print(f"✅ Лучший метод: {best_method} (score: {best_score:.3f})", file=sys.stderr)
    return best_labels

def transcribe_with_whisper(audio_path, language='ru', model_size='small'):
    """Транскрипция через faster-whisper (без изменений)"""
    print(f"🎤 Начинаем транскрипцию Whisper...", file=sys.stderr)
    
    try:
        from faster_whisper import WhisperModel
        
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, info = model.transcribe(
            audio_path, 
            language=language,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
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
        
        print(f"✅ Whisper транскрипция завершена: {len(whisper_segments)} сегментов", file=sys.stderr)
        
        return {
            'text': full_text.strip(),
            'segments': whisper_segments,
            'language': info.language,
            'language_probability': info.language_probability
        }
        
    except Exception as e:
        print(f"❌ Ошибка Whisper: {e}", file=sys.stderr)
        return None

def enhanced_diarization(audio_path, num_speakers=None):
    """Улучшенная диаризация на основе тембра голоса"""
    print(f"👥 УЛУЧШЕННАЯ диаризация (Enhanced Voice Timbre Analysis)...", file=sys.stderr)
    
    try:
        import torchaudio
        
        # Инициализируем анализатор
        analyzer = EnhancedVoiceAnalyzer()
        analyzer.load_models()
        
        # Загружаем аудио
        waveform, sample_rate = torchaudio.load(audio_path)
        
        # Конвертируем в моно
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0)
        
        # Ресемплируем если нужно
        if sample_rate != analyzer.sample_rate:
            resampler = torchaudio.transforms.Resample(sample_rate, analyzer.sample_rate)
            waveform = resampler(waveform)
        
        waveform_np = waveform.numpy()
        
        # Адаптивная сегментация
        segments = analyzer.adaptive_segmentation(waveform_np)
        
        # Извлекаем расширенные голосовые характеристики
        print("🔍 Извлекаем расширенные голосовые характеристики...", file=sys.stderr)
        voice_features = []
        valid_segments = []
        
        for start_time, end_time in segments:
            start_sample = int(start_time * analyzer.sample_rate)
            end_sample = int(end_time * analyzer.sample_rate)
            segment_waveform = waveform_np[start_sample:end_sample]
            
            if len(segment_waveform) > analyzer.sample_rate * 0.5:  # Минимум 0.5 сек
                try:
                    features = analyzer.extract_voice_features(segment_waveform, start_time, end_time)
                    voice_features.append(features['features'])
                    valid_segments.append({
                        'start': start_time,
                        'end': end_time,
                        'f0_mean': features['f0_mean'],
                        'spectral_centroid': features['spectral_centroid'],
                        'speech_rate': features['speech_rate']
                    })
                except Exception as e:
                    print(f"⚠️ Ошибка анализа сегмента {start_time:.2f}-{end_time:.2f}: {e}", file=sys.stderr)
                    continue
        
        if len(voice_features) == 0:
            print("❌ Не удалось извлечь голосовые характеристики", file=sys.stderr)
            return None
        
        print(f"✅ Извлечено характеристик: {len(voice_features)}", file=sys.stderr)
        
        # Улучшенная кластеризация
        labels = enhanced_clustering(voice_features, num_speakers)
        
        # Создаем результат диаризации
        diarization_segments = []
        speakers = set()
        
        for i, segment in enumerate(valid_segments):
            speaker_id = f"SPEAKER_{labels[i]:02d}"
            diarization_segments.append({
                'start': segment['start'],
                'end': segment['end'],
                'speaker': speaker_id,
                'voice_characteristics': {
                    'f0_mean': float(segment['f0_mean']) if not np.isnan(segment['f0_mean']) else 0,
                    'spectral_centroid': float(segment['spectral_centroid']),
                    'speech_rate': float(segment['speech_rate'])
                }
            })
            speakers.add(speaker_id)
        
        # Объединяем соседние сегменты одного говорящего
        merged_segments = merge_adjacent_segments(diarization_segments)
        
        print(f"✅ Улучшенная диаризация завершена", file=sys.stderr)
        print(f"   👥 Найдено говорящих: {len(speakers)}", file=sys.stderr)
        print(f"   🎯 Финальных сегментов: {len(merged_segments)}", file=sys.stderr)
        
        return {
            'segments': merged_segments,
            'speakers': list(speakers),
            'speaker_count': len(speakers),
            'method': 'enhanced_voice_timbre_analysis'
        }
        
    except Exception as e:
        print(f"❌ Ошибка улучшенной диаризации: {e}", file=sys.stderr)
        print(f"❌ Traceback: {traceback.format_exc()}", file=sys.stderr)
        return None

def merge_adjacent_segments(segments):
    """Объединение соседних сегментов одного говорящего"""
    if not segments:
        return []
    
    merged = []
    current = None
    max_gap = 1.5  # Максимальный разрыв для объединения
    
    for segment in sorted(segments, key=lambda x: x['start']):
        if current is None or current['speaker'] != segment['speaker'] or (segment['start'] - current['end']) > max_gap:
            if current:
                merged.append(current)
            current = segment.copy()
        else:
            current['end'] = segment['end']
            # Усредняем голосовые характеристики
            if 'voice_characteristics' in current and 'voice_characteristics' in segment:
                for key in current['voice_characteristics']:
                    current['voice_characteristics'][key] = (
                        current['voice_characteristics'][key] + segment['voice_characteristics'][key]
                    ) / 2
    
    if current:
        merged.append(current)
    
    return merged

def combine_transcription_and_diarization(whisper_result, diarization_result):
    """Объединение результатов (улучшенная версия)"""
    print("🔗 Объединяем транскрипцию и улучшенную диаризацию...", file=sys.stderr)
    
    if not whisper_result or not diarization_result:
        return None
    
    whisper_segments = whisper_result['segments']
    diarization_segments = diarization_result['segments']
    
    combined_segments = []
    
    for w_seg in whisper_segments:
        w_start, w_end = w_seg['start'], w_seg['end']
        w_text = w_seg['text']
        
        # Находим лучшее совпадение по времени
        best_speaker = "SPEAKER_00"
        best_characteristics = {}
        max_overlap = 0
        
        for d_seg in diarization_segments:
            d_start, d_end = d_seg['start'], d_seg['end']
            
            overlap_start = max(w_start, d_start)
            overlap_end = min(w_end, d_end)
            overlap_duration = max(0, overlap_end - overlap_start)
            
            if overlap_duration > max_overlap:
                max_overlap = overlap_duration
                best_speaker = d_seg['speaker']
                best_characteristics = d_seg.get('voice_characteristics', {})
        
        combined_segments.append({
            'start': w_start,
            'end': w_end,
            'text': w_text,
            'speaker': best_speaker,
            'voice_characteristics': best_characteristics,
            'words': w_seg.get('words', [])
        })
    
    # Группируем с учетом голосовых характеристик
    grouped_segments = group_by_voice_similarity(combined_segments)
    
    return {
        'text': whisper_result['text'],
        'segments': grouped_segments,
        'speaker_count': diarization_result['speaker_count'],
        'speakers': diarization_result['speakers'],
        'language': whisper_result['language'],
        'language_probability': whisper_result['language_probability'],
        'diarization_method': diarization_result.get('method', 'enhanced')
    }

def group_by_voice_similarity(segments):
    """Группировка сегментов с учетом схожести голосовых характеристик"""
    if not segments:
        return []
    
    grouped = []
    current_group = None
    max_pause = 2.0
    
    for segment in segments:
        should_start_new = (
            current_group is None or
            current_group['speaker'] != segment['speaker'] or
            (segment['start'] - current_group['end']) > max_pause
        )
        
        if should_start_new:
            if current_group:
                grouped.append(current_group)
            current_group = {
                'start': segment['start'],
                'end': segment['end'],
                'text': segment['text'],
                'speaker': segment['speaker'],
                'voice_characteristics': segment.get('voice_characteristics', {}),
                'confidence': 1.0
            }
        else:
            current_group['end'] = segment['end']
            current_group['text'] += ' ' + segment['text']
            
            # Проверяем схожесть голосовых характеристик
            if 'voice_characteristics' in segment and current_group['voice_characteristics']:
                similarity = calculate_voice_similarity(
                    current_group['voice_characteristics'],
                    segment['voice_characteristics']
                )
                current_group['confidence'] = min(current_group.get('confidence', 1.0), similarity)
    
    if current_group:
        grouped.append(current_group)
    
    return grouped

def calculate_voice_similarity(char1, char2):
    """Вычисление схожести голосовых характеристик"""
    if not char1 or not char2:
        return 0.5
    
    similarities = []
    
    # Сравниваем F0 (основную частоту)
    if 'f0_mean' in char1 and 'f0_mean' in char2:
        f0_diff = abs(char1['f0_mean'] - char2['f0_mean'])
        f0_sim = max(0, 1 - f0_diff / 200)  # Нормализуем по 200 Гц
        similarities.append(f0_sim)
    
    # Сравниваем спектральный центроид
    if 'spectral_centroid' in char1 and 'spectral_centroid' in char2:
        sc_diff = abs(char1['spectral_centroid'] - char2['spectral_centroid'])
        sc_sim = max(0, 1 - sc_diff / 2000)  # Нормализуем по 2000 Гц
        similarities.append(sc_sim)
    
    # Сравниваем темп речи
    if 'speech_rate' in char1 and 'speech_rate' in char2:
        sr_diff = abs(char1['speech_rate'] - char2['speech_rate'])
        sr_sim = max(0, 1 - sr_diff / 10)  # Нормализуем по 10 событий/сек
        similarities.append(sr_sim)
    
    return np.mean(similarities) if similarities else 0.5

def timbre_focused_diarization(audio_path, num_speakers=None):
    """Диаризация с акцентом на тембр голоса, а не на время"""
    print(f"🎵 ТЕМБР-ОРИЕНТИРОВАННАЯ диаризация (Timbre-First Analysis)...", file=sys.stderr)
    
    try:
        import torchaudio
        from sklearn.cluster import DBSCAN
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import silhouette_score
        
        # Инициализируем анализатор
        analyzer = EnhancedVoiceAnalyzer()
        analyzer.load_models()
        
        # Загружаем аудио
        waveform, sample_rate = torchaudio.load(audio_path)
        
        # Конвертируем в моно
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0)
        
        # Ресемплируем если нужно
        if sample_rate != analyzer.sample_rate:
            resampler = torchaudio.transforms.Resample(sample_rate, analyzer.sample_rate)
            waveform = resampler(waveform)
        
        waveform_np = waveform.numpy()
        
        # КЛЮЧЕВОЕ ОТЛИЧИЕ: детальный анализ каждые 200ms
        voice_analysis = analyzer.fine_grained_voice_analysis(waveform_np)
        
        if len(voice_analysis) == 0:
            print("❌ Не удалось извлечь голосовые характеристики", file=sys.stderr)
            return None
        
        print(f"🔬 Анализируем {len(voice_analysis)} микро-сегментов...", file=sys.stderr)
        
        # Извлекаем только высококачественные сегменты
        high_quality_segments = [
            seg for seg in voice_analysis 
            if seg['confidence'] > 0.5 and not np.isnan(seg['f0_mean']) and seg['f0_mean'] > 0
        ]
        
        print(f"✅ Высококачественных сегментов: {len(high_quality_segments)}", file=sys.stderr)
        
        if len(high_quality_segments) < 10:
            print("⚠️ Слишком мало качественных сегментов, используем все", file=sys.stderr)
            high_quality_segments = voice_analysis
        
        # Кластеризация на основе ТЕМБРА, а не времени
        features_array = np.array([seg['features'] for seg in high_quality_segments])
        
        # Нормализация с акцентом на голосовые характеристики
        scaler = StandardScaler()
        features_normalized = scaler.fit_transform(features_array)
        
        # Используем DBSCAN для автоматического определения количества кластеров
        # на основе плотности голосовых характеристик
        best_labels = None
        best_score = -1
        best_eps = None
        
        # Пробуем разные параметры DBSCAN
        eps_values = np.arange(0.3, 2.0, 0.1)
        min_samples_values = [3, 5, 7]
        
        for eps in eps_values:
            for min_samples in min_samples_values:
                try:
                    clustering = DBSCAN(eps=eps, min_samples=min_samples)
                    labels = clustering.fit_predict(features_normalized)
                    
                    # Исключаем шум (-1)
                    unique_labels = set(labels)
                    if -1 in unique_labels:
                        unique_labels.remove(-1)
                    
                    if len(unique_labels) >= 2 and len(unique_labels) <= 8:
                        # Вычисляем silhouette score только для не-шумовых точек
                        non_noise_mask = labels != -1
                        if np.sum(non_noise_mask) > 1:
                            score = silhouette_score(
                                features_normalized[non_noise_mask], 
                                labels[non_noise_mask]
                            )
                            
                            print(f"   🎯 DBSCAN eps={eps:.1f}, min_samples={min_samples}: "
                                  f"{len(unique_labels)} кластеров, score={score:.3f}", file=sys.stderr)
                            
                            if score > best_score:
                                best_score = score
                                best_labels = labels
                                best_eps = eps
                                
                except Exception as e:
                    continue
        
        # Fallback если DBSCAN не сработал
        if best_labels is None:
            print("⚠️ DBSCAN не сработал, используем Agglomerative", file=sys.stderr)
            from sklearn.cluster import AgglomerativeClustering
            n_clusters = num_speakers if num_speakers else min(4, len(high_quality_segments) // 5)
            clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
            best_labels = clustering.fit_predict(features_normalized)
            best_eps = "fallback"
        
        # Обрабатываем шумовые точки (если есть)
        noise_points = np.sum(best_labels == -1)
        if noise_points > 0:
            print(f"⚠️ Найдено {noise_points} шумовых точек, переназначаем к ближайшим кластерам", file=sys.stderr)
            # Переназначаем шумовые точки к ближайшим кластерам
            from sklearn.neighbors import NearestNeighbors
            
            non_noise_mask = best_labels != -1
            if np.sum(non_noise_mask) > 0:
                nn = NearestNeighbors(n_neighbors=1)
                nn.fit(features_normalized[non_noise_mask])
                
                noise_mask = best_labels == -1
                if np.sum(noise_mask) > 0:
                    distances, indices = nn.kneighbors(features_normalized[noise_mask])
                    best_labels[noise_mask] = best_labels[non_noise_mask][indices.flatten()]
        
        unique_speakers = len(set(best_labels))
        print(f"✅ Тембр-ориентированная кластеризация завершена", file=sys.stderr)
        print(f"   🎵 Найдено говорящих: {unique_speakers}", file=sys.stderr)
        print(f"   🎯 Лучший параметр: eps={best_eps}, score={best_score:.3f}", file=sys.stderr)
        
        # Создаем результат диаризации
        diarization_segments = []
        speakers = set()
        
        for i, segment in enumerate(high_quality_segments):
            speaker_id = f"SPEAKER_{best_labels[i]:02d}"
            diarization_segments.append({
                'start': segment['start_time'],
                'end': segment['end_time'],
                'speaker': speaker_id,
                'voice_characteristics': {
                    'f0_mean': float(segment['f0_mean']) if not np.isnan(segment['f0_mean']) else 0,
                    'f0_std': float(segment['f0_std']) if not np.isnan(segment['f0_std']) else 0,
                    'spectral_centroid': float(segment['spectral_centroid']),
                    'energy': float(segment['energy']),
                    'confidence': float(segment['confidence'])
                }
            })
            speakers.add(speaker_id)
        
        # Объединяем близкие по времени сегменты одного говорящего
        merged_segments = merge_timbre_segments(diarization_segments)
        
        print(f"✅ Тембр-ориентированная диаризация завершена", file=sys.stderr)
        print(f"   👥 Финальных говорящих: {len(speakers)}", file=sys.stderr)
        print(f"   🎯 Финальных сегментов: {len(merged_segments)}", file=sys.stderr)
        
        return {
            'segments': merged_segments,
            'speakers': list(speakers),
            'speaker_count': len(speakers),
            'method': 'timbre_focused_analysis',
            'analysis_frequency': '200ms',
            'quality_threshold': 0.5
        }
        
    except Exception as e:
        print(f"❌ Ошибка тембр-ориентированной диаризации: {e}", file=sys.stderr)
        print(f"❌ Traceback: {traceback.format_exc()}", file=sys.stderr)
        return None

def merge_timbre_segments(segments):
    """Объединение сегментов на основе тембра и близости по времени"""
    if not segments:
        return []
    
    # Сортируем по времени
    sorted_segments = sorted(segments, key=lambda x: x['start'])
    merged = []
    current_group = []
    
    for segment in sorted_segments:
        if not current_group:
            current_group = [segment]
        else:
            last_segment = current_group[-1]
            
            # Проверяем: тот же говорящий И близко по времени (до 0.5 сек)
            same_speaker = last_segment['speaker'] == segment['speaker']
            close_in_time = (segment['start'] - last_segment['end']) <= 0.5
            
            if same_speaker and close_in_time:
                current_group.append(segment)
            else:
                # Завершаем текущую группу
                if current_group:
                    merged_segment = merge_segment_group(current_group)
                    merged.append(merged_segment)
                current_group = [segment]
    
    # Добавляем последнюю группу
    if current_group:
        merged_segment = merge_segment_group(current_group)
        merged.append(merged_segment)
    
    return merged

def merge_segment_group(segment_group):
    """Объединяет группу сегментов в один"""
    if len(segment_group) == 1:
        return segment_group[0]
    
    # Берем временные границы
    start_time = segment_group[0]['start']
    end_time = segment_group[-1]['end']
    speaker = segment_group[0]['speaker']
    
    # Усредняем голосовые характеристики
    characteristics = {}
    for key in segment_group[0]['voice_characteristics']:
        values = [seg['voice_characteristics'][key] for seg in segment_group]
        characteristics[key] = np.mean(values)
    
    return {
        'start': start_time,
        'end': end_time,
        'speaker': speaker,
        'voice_characteristics': characteristics
    }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Использование: python transcription_service_enhanced.py <audio_file> [language] [model_size] [num_speakers]"
        }))
        sys.exit(1)
    
    audio_file = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else 'ru'
    model_size = sys.argv[3] if len(sys.argv) > 3 else 'small'
    num_speakers = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else None
    
    print(f"🎯 УЛУЧШЕННАЯ ОБРАБОТКА v3.3.0:", file=sys.stderr)
    print(f"   📁 Аудио файл: {audio_file}", file=sys.stderr)
    print(f"   🌍 Язык: {language}", file=sys.stderr)
    print(f"   🤖 Модель Whisper: {model_size}", file=sys.stderr)
    print(f"   👥 Количество говорящих: {num_speakers or 'авто'}", file=sys.stderr)
    
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
            "error": "Не все необходимые библиотеки установлены"
        }))
        sys.exit(1)
    
    try:
        # Транскрипция
        print("🎤 Этап 1: Транскрипция...", file=sys.stderr)
        whisper_result = transcribe_with_whisper(audio_file, language, model_size)
        if not whisper_result:
            raise Exception("Ошибка транскрипции")
        
        # Улучшенная диаризация (по умолчанию enhanced, можно переключить на timbre)
        method = os.environ.get('DIARIZATION_METHOD', 'enhanced')
        if method == 'timbre':
            print("🎵 Этап 2: Тембр-ориентированная диаризация...", file=sys.stderr)
            diarization_result = timbre_focused_diarization(audio_file, num_speakers)
        else:
            print("🧠 Этап 2: Улучшенная диаризация...", file=sys.stderr)
            diarization_result = enhanced_diarization(audio_file, num_speakers)
        
        if not diarization_result:
            raise Exception("Ошибка диаризации")
        
        # Объединение результатов
        print("🔗 Этап 3: Объединение результатов...", file=sys.stderr)
        final_result = combine_transcription_and_diarization(whisper_result, diarization_result)
        if not final_result:
            raise Exception("Ошибка объединения результатов")
        
        # Выводим результат
        result = {
            "success": True,
            "text": final_result['text'],
            "segments": final_result['segments'],
            "speaker_count": final_result['speaker_count'],
            "speakers": final_result['speakers'],
            "language": final_result['language'],
            "language_probability": final_result['language_probability'],
            "processing_method": "enhanced_voice_timbre_analysis_v3.3.0"
        }
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 