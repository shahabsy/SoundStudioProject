from PyQt5.QtCore import pyqtSignal, QObject, QTimer, QMutex, Qt
import pygame
import logging
import os, sys
import numpy as np
import wave, time
from core.audio_meter import BarMeter
from pydub import AudioSegment
from core.utils import resource_path

class AudioWorker(QObject):
    playback_started = pyqtSignal(str)
    playback_stopped = pyqtSignal(str)
    playback_finished = pyqtSignal(str)
    levels_updated = pyqtSignal(str, float, float)
    master_levels_updated = pyqtSignal(str, float, float)
    master_playback_stopped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        try:
            pygame.mixer.init(frequency=44100, size=16, channels=2, buffer=1024)
            pygame.mixer.set_num_channels(32)  # Increase channel count for better handling
        except Exception as e:
            print("pygame.mixer.init failed:", e)
        # Audio analysis params
        self.sample_rate = 44100
        self.channels = 2
        self.buffer_size = 1024
        self.samples_per_update = self.buffer_size * 2
        # Timer setup(aligned to buffer updates)
        self.update_interval = (self.samples_per_update / self.sample_rate) * 1000 #ms
        self.level_timer = QTimer()
        self.level_timer.setTimerType(Qt.PreciseTimer)
        self.level_timer.setInterval(int(self.update_interval))
        self.level_timer.timeout.connect(self.update_levels)
        self.last_update_time = time.perf_counter()
        
        # State Tracking
        self.mutex = QMutex()
        self.active_channels = {}
        self.sound_cache = {}
        self.level_data = {}
        self.loop_flags = {}
        self.last_buffer_time = time.time()
        self.audio_meter = BarMeter()
        self.audio_volumes = {}
        self._min_db = self.audio_meter._min_db
        
        # For fade effect tracking
        self.fade_effects = {}
        
        self.fader_timers = {}
        logging.info("AudioWorker initialized")
    
    def load_audio(self, audio_id, file_path):
        self.mutex.lock()
        try:
            FFMPEG = resource_path("ffmpeg")
            if sys.platform == "darwin":
                ffmpeg_bin = os.path.join(FFMPEG, "ffmpeg")
                ffprobe_bin = os.path.join(FFMPEG, "ffprobe")
            else:
                ffmpeg_bin = os.path.join(FFMPEG, "ffmpeg.exe")
                ffprobe_bin = os.path.join(FFMPEG, "ffprobe.exe")
        
            AudioSegment.converter = ffmpeg_bin
            AudioSegment.ffprobe = ffprobe_bin
            
            if audio_id not in self.sound_cache:
                if not os.path.exists(file_path):
                    logging.error(f"File not found: {file_path}")
                    return False 
                try:
                    sound = pygame.mixer.Sound(file_path)
                    self.sound_cache[audio_id] = sound
                    self.loop_flags[audio_id] = False

                    nAudio = AudioSegment.from_file(file_path)
                    nSamples = np.array(nAudio.get_array_of_samples())
                    nSample_rate = nAudio.frame_rate
                    nChannels = nAudio.channels
                    nDuration = len(nAudio) / 1000.0
                    nSample_width = nAudio.sample_width
                    nMax_val = float(2**(8*nSample_width-1))
                    
                    if nChannels > 1:
                        nSamples = nSamples.reshape(-1, nChannels)
                    
                    self.level_data[audio_id] = {
                            'samples': nSamples,
                            'sample_width': nSample_width,
                            'channels': nChannels,
                            'ptr': 0,
                            'max_val' : nMax_val,
                            'duration' : nDuration,
                        }
                except pygame.error as e:
                    logging.error(f"Pygame error loading: {file_path}: {str(e)}")
                    return False
            elif audio_id in self.sound_cache:
                try:
                    sound = pygame.mixer.Sound(file_path)
                    self.sound_cache[audio_id] = sound
                    self.loop_flags[audio_id] = False

                    nAudio = AudioSegment.from_file(file_path)
                    nSamples = np.array(nAudio.get_array_of_samples())
                    nSample_rate = nAudio.frame_rate
                    nChannels = nAudio.channels
                    nDuration = len(nAudio) / 1000.0
                    nSample_width = nAudio.sample_width
                    nMax_val = float(2**(8*nSample_width-1))
                    
                    if nChannels > 1:
                        nSamples = nSamples.reshape(-1, nChannels)
                    
                    self.level_data[audio_id] = {
                            'samples': nSamples,
                            'sample_width': nSample_width,
                            'channels': nChannels,
                            'ptr': 0,
                            'max_val' : nMax_val,
                            'duration' : nDuration,
                        }
                except pygame.error as e:
                    logging.error(f"Pygame error loading: {file_path}: {str(e)}")
                    return False
            return False
        finally:
            self.mutex.unlock()
    
    def play(self, audio_id, loop, fade_in=0.0, fade_out=0.0):
        self.mutex.lock()
        try:
            if audio_id not in self.sound_cache:
                logging.warning(f"Audio {audio_id} not loaded")
                return
            
            # Stop any existing playback for this ID
            self._stop_playback(audio_id)

            if audio_id in self.level_data:
                self.level_data[audio_id]['ptr'] = 0

            # Start new playback
            self.loop_flags[audio_id] = loop
            loops = -1 if loop else 0

            fade_in_ms = int(fade_in * 1000) if fade_in else 0
            
            # Get current volume
            current_volume = self.audio_volumes.get(audio_id, 1.0)
            
            # For looped audio with fade effects, we need a special approach
            if loop and (fade_in > 0 or fade_out > 0):
                # Use a custom approach for looped audio with fade effects
                channel = self._play_looped_with_fade(audio_id, fade_in, fade_out, current_volume)
            else:
                # Standard playback for non-looped or looped without fade effects
                channel = self.sound_cache[audio_id].play(loops=loops, fade_ms=fade_in_ms)
                
                # Set initial volume on the channel
                if channel:
                    channel.set_volume(current_volume)

            # Track fade in/out for metering
            now = time.time()
            self.level_data[audio_id]['fade_in'] = fade_in
            self.level_data[audio_id]['fade_out'] = fade_out
            self.level_data[audio_id]['play_start'] = now
            
            # For looped audio, we need to handle fade out differently
            if loop:
                self.level_data[audio_id]['fade_out_start'] = None
                # Store the loop duration for later use in update_levels
                self.level_data[audio_id]['loop_duration'] = self.level_data[audio_id]['duration']
            else:
                # For non-looped audio, calculate when to start fade out
                duration = self.level_data[audio_id]['duration']
                fade_out_start = now + max(0, duration - fade_out)
                self.level_data[audio_id]['fade_out_start'] = fade_out_start
            
            if channel:
                self.active_channels[audio_id] = channel
                if not self.level_timer.isActive():
                    self.last_buffer_time = time.time()
                    self.level_timer.start()

                self.playback_started.emit(audio_id)
                self._monitor_playback(audio_id)
                
                # Handle fade out for non-looped audio
                if fade_out > 0 and not loop:
                    QTimer.singleShot(int((duration - fade_out) * 1000), 
                                     lambda: self._start_fadeout(audio_id, fade_out))
                    
        finally:
            self.mutex.unlock()
    
    def _play_looped_with_fade(self, audio_id, fade_in, fade_out, volume):
        """Special method for playing looped audio with fade effects"""
        # Create a custom channel for this audio
        #channel = pygame.mixer.Channel(pygame.mixer.get_num_channels() - 1)
        channel = pygame.mixer.find_channel()
        if channel is None:
            return None
        
        # Store fade information
        now = time.time()
        self.fade_effects[audio_id] = {
            'fade_in': fade_in,
            'fade_out': fade_out,
            'volume': volume,
            'channel': channel,
            'last_loop_time': now,
            'loop_duration': self.level_data[audio_id]['duration'],
            'play_start': now
        }
        
        # Start the first loop with fade in
        channel.set_volume(0)  # Start at zero volume for fade in
        channel.play(self.sound_cache[audio_id], loops=-1)
        
        # Start a timer to handle the fade effects
        self._update_looped_fade(audio_id)
        
        return channel
    
    def _update_looped_fade(self, audio_id):
        """Update fade effects for looped audio"""
        if audio_id not in self.fade_effects:
            return
            
        fade_info = self.fade_effects[audio_id]
        channel = fade_info['channel']
        fade_in = fade_info['fade_in']
        fade_out = fade_info['fade_out']
        volume = fade_info['volume']
        loop_duration = fade_info['loop_duration']
        
        # Calculate position in current loop
        current_time = time.time()
        elapsed_in_loop = (current_time - fade_info['last_loop_time']) % loop_duration
        
        # Calculate volume based on position in loop
        if elapsed_in_loop < fade_in:
            # Fade in phase
            gain = elapsed_in_loop / fade_in
        elif elapsed_in_loop > (loop_duration - fade_out):
            # Fade out phase
            time_into_fadeout = elapsed_in_loop - (loop_duration - fade_out)
            gain = 1.0 - (time_into_fadeout / fade_out)
        else:
            # Full volume phase
            gain = 1.0
        
        # Apply the calculated gain and user volume
        channel.set_volume(volume * gain)
        
        # Update the last loop time if we've completed a loop
        if elapsed_in_loop < (current_time - fade_info['last_loop_time'] - loop_duration):
            fade_info['last_loop_time'] = current_time - elapsed_in_loop
        
        # Schedule next update
        QTimer.singleShot(50, lambda: self._update_looped_fade(audio_id))
    
    def _start_fadeout(self, audio_id, fade_out):
        self.mutex.lock()
        try:
            if audio_id in self.active_channels:
                channel = self.active_channels[audio_id]
                channel.fadeout(int(fade_out * 1000))
        finally:
            self.mutex.unlock()
    
    def update_levels(self):
        self.mutex.lock()
        try:
            for audio_id, channel in self.active_channels.items():
                if audio_id not in self.level_data:
                    continue
                
                data = self.level_data[audio_id]
                channels = data['channels']
                sample_width = data['sample_width']
                samples = data['samples']
                max_val = data.get('max_val', float(2**(8*sample_width-1)))
                
                chunk_size = self.samples_per_update * channels
                start = data['ptr']
                end = min(data['ptr'] + chunk_size, len(samples))
                chunk = data['samples'][start:end]
                
                # Handle wrap around for looped audio
                if len(chunk) < chunk_size:
                    if self.loop_flags.get(audio_id, False):
                        remaining = chunk_size - len(chunk)
                        chunk = np.concatenate((chunk, data['samples'][:remaining]))
                    else:
                        chunk = np.pad(chunk, (0, chunk_size - len(chunk)), 'constant')

                # Split into left and right channels
                if channels == 2:
                    left = chunk[::2]
                    right = chunk[1::2]
                else:
                    left = right = chunk
                
                # Apply fade in and out to metering
                gain = 1.0
                now = time.time()
                fade_in = data.get('fade_in', 0.0)
                fade_out = data.get('fade_out', 0.0)
                play_start = data.get('play_start', None)
                fade_out_start = data.get('fade_out_start', None)
                
                if play_start is not None:
                    elapsed = now - play_start
                    
                    # For looped audio, calculate position within current loop
                    if self.loop_flags.get(audio_id, False):
                        loop_duration = data.get('loop_duration', data['duration'])
                        position_in_loop = elapsed % loop_duration
                        
                        # Apply fade in at the beginning of each loop
                        if fade_in > 0 and position_in_loop < fade_in:
                            gain = position_in_loop / fade_in
                        
                        # Apply fade out at the end of each loop
                        if fade_out > 0 and position_in_loop > (loop_duration - fade_out):
                            time_into_fadeout = position_in_loop - (loop_duration - fade_out)
                            gain = 1.0 - (time_into_fadeout / fade_out)
                    else:
                        # Non-looped audio - use original logic
                        if fade_in > 0 and elapsed < fade_in:
                            gain = elapsed / fade_in
                        
                        if fade_out and fade_out_start and now >= fade_out_start:
                            time_into_fadeout = now - fade_out_start
                            if time_into_fadeout < fade_out:
                                gain = 1.0 - (time_into_fadeout / fade_out)
                            else:
                                gain = 0.0
                
                # For looped audio with custom fade handling, get the actual gain from the fade effects
                if audio_id in self.fade_effects:
                    fade_info = self.fade_effects[audio_id]
                    elapsed_in_loop = (now - fade_info['last_loop_time']) % fade_info['loop_duration']
                    
                    if elapsed_in_loop < fade_info['fade_in']:
                        gain = elapsed_in_loop / fade_info['fade_in']
                    elif elapsed_in_loop > (fade_info['loop_duration'] - fade_info['fade_out']):
                        time_into_fadeout = elapsed_in_loop - (fade_info['loop_duration'] - fade_info['fade_out'])
                        gain = 1.0 - (time_into_fadeout / fade_info['fade_out'])
                    else:
                        gain = 1.0
                
                # Apply user volume to the gain
                user_volume = self.audio_volumes.get(audio_id, 1.0)
                gain *= user_volume
                
                # Calculate RMS and convert to dB
                def calculate_db(samples):
                    samples_float = samples.astype(np.float32) * gain
                    peak = np.max(np.abs(samples_float)) / max_val
                    return 20 * np.log10(peak + 1e-10)
                    
                left_db = calculate_db(left)
                right_db = calculate_db(right)

                self.levels_updated.emit(audio_id, left_db, right_db)          
                
                # Update pointer position
                if samples.ndim == 2:
                    advance = self.samples_per_update
                    total = len(samples)
                else:
                    advance = self.samples_per_update * channels
                    total = len(samples)
                
                if self.loop_flags.get(audio_id, False):
                    data['ptr'] = (data['ptr'] + advance) % total
                else:
                    data['ptr'] = min(data['ptr'] + advance, total)

            if not self.active_channels:
                self.level_timer.stop()
                
        except Exception as e:
            logging.error(f"Level calculation error: {str(e)}")
        finally:
            self.mutex.unlock()
    
    def _monitor_playback(self, audio_id):
        def check_status():
            self.mutex.lock()
            try:
                channel = self.active_channels.get(audio_id)
                if not channel:
                    return
                
                if not channel.get_busy():
                    if self.loop_flags.get(audio_id, False):
                        # For looped audio, we need to check if it's still playing
                        # Looping is handled by pygame when loops= -1
                        # Check again after delay
                        QTimer.singleShot(100, check_status)
                    else:
                        # Clean up finished playback
                        if audio_id in self.active_channels:
                            del self.active_channels[audio_id]
                        if audio_id in self.fade_effects:
                            del self.fade_effects[audio_id]
                        self.playback_finished.emit(audio_id)
                        self.levels_updated.emit(audio_id, self.audio_meter._min_db, self.audio_meter._min_db)
                else:
                    # Check again after delay
                    QTimer.singleShot(100, check_status)
            finally:
                self.mutex.unlock()
        QTimer.singleShot(100, check_status)
    
    def stop(self, audio_id):
        self.mutex.lock()
        try:
            self._stop_playback(audio_id)
            self.levels_updated.emit(audio_id, self._min_db, self._min_db)
            self.playback_stopped.emit(audio_id)
        finally:
            self.mutex.unlock()
    
    def _stop_playback(self, audio_id):
        if audio_id in self.active_channels:
            self.active_channels[audio_id].stop()
            del self.active_channels[audio_id]
            if audio_id in self.fade_effects:
                del self.fade_effects[audio_id]
            if hasattr(self, "audio_volumes") and audio_id in self.audio_volumes:
                del self.audio_volumes[audio_id]
        if not self.active_channels and self.level_timer.isActive():
            self.level_timer.stop()
            
    def stop_all(self):
        self.mutex.lock()
        try:
            for audio_id in list(self.active_channels.keys()):
                self._stop_playback(audio_id)
                self.levels_updated.emit(audio_id, self._min_db, self._min_db)
                self.playback_stopped.emit(audio_id)
        finally:
            self.mutex.unlock()
    
    def set_volume(self, audio_id, volume):
        self.mutex.lock()
        try:
            if audio_id in self.sound_cache:
                pygame_volume = volume / 100
                self.sound_cache[audio_id].set_volume(pygame_volume)
                self.audio_volumes[audio_id] = pygame_volume
                
                # Update volume for active playback
                if audio_id in self.active_channels:
                    channel = self.active_channels[audio_id]
                    
                    # For looped audio with fade effects, update the fade info
                    if audio_id in self.fade_effects:
                        self.fade_effects[audio_id]['volume'] = pygame_volume
                    else:
                        # For standard playback, set volume directly
                        channel.set_volume(pygame_volume)
        finally:
            self.mutex.unlock()
    
    def cleanup(self):
        self.stop_all()
        self.level_timer.stop()
        pygame.mixer.quit()