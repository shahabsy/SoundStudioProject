from PyQt5.QtCore import QThread, QObject, QTimer
from core.audio_worker import AudioWorker


class AudioPlayer(QObject):
    def __init__(self):
        super().__init__()
        self.worker = AudioWorker()
        self.thread = QThread()
        # move worker to thread before starting
        self.worker.moveToThread(self.thread)

        # connect worker signals
        self.worker.playback_started.connect(self.on_playback_started)
        self.worker.playback_stopped.connect(self.on_playback_stopped)
        self.worker.playback_finished.connect(self.on_playback_finished)
        self.worker.levels_updated.connect(self.on_levels_updated)
        self.worker.master_levels_updated.connect(self.on_master_levels_updated)
        self.worker.master_playback_stopped.connect(self.on_master_playback_stopped)

        # start the thread
        self.thread.start()
    
    def on_playback_started(self, audio_id):
        print(f"Playback started now: {audio_id}")
    
    def on_playback_stopped(self, audio_id):
        print(f"Playback stopped: { audio_id}")
    
    def on_playback_finished(self, audio_id):
        print(f"Playback finished: { audio_id}")
    
    def on_levels_updated(self, audio_id, left_db, right_db):
        pass
        #db_level = -60 + (60 * level) if level > 0 else -60
        #print(f"Level update - {audio_id} : {left_db:.1f}dB - {right_db:.1f}dB")
    
    def on_master_levels_updated(self, audio_id, left_db, right_db):
        pass
        #print(f"Master Level update - {audio_id} : {left_db:.1f}dB - {right_db:.1f}dB")
    
    def on_master_playback_stopped(self, audio_id):
        print(f"Playback stopped: { audio_id}")

    def execute_in_thread(self, func, *args):
        # execture a function in the worker thread
        print(f"args: {args}")
        QTimer.singleShot(0, lambda: func(*args))

    def load_file(self, audio_id, file_path):
        # use QTimer to run in worker thread context
        self.execute_in_thread(self.worker.load_audio, audio_id, file_path)
    
    def play(self, audio_id, loop=False, fade_in=0.0, fade_out=0.0):
        self.execute_in_thread(self.worker.play, audio_id, loop, fade_in, fade_out)
        print(f"player sending loop {loop},  fade in {fade_in}, and fade out { fade_out}")
    
    def stop(self, audio_id):
        self.execute_in_thread(self.worker.stop, audio_id)

    def stop_all(self):
        self.execute_in_thread(self.worker.stop_all)
    
    def set_volume(self, audio_id, volume):
        self.execute_in_thread(self.worker.set_volume, audio_id, volume)
    
    def cleanup(self):
        # to be called only on application exit
        self.execute_in_thread(self.worker.stop_all)
        self.thread.quit()
        self.thread.wait() # we can add wait in seconds like 2 or 3 etc..
