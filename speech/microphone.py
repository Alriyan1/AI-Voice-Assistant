import pyaudio
import threading
from typing import Optional,Callable,Generator
from loguru import logger
import numpy as np

class MicrophoneManager:
    def __init__(self,sample_rate: int=16000,chuck_size: int=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chuck_size
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_listening= False
        self._stop_event = threading.Event()
        self._audio_queue: list = []
        self._lock = threading.Lock()

    
    def list_devices(self) -> list:
        devices = []
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append({
                    'index':i,
                    'name':info['name'],
                    'channels':info['maxInputChannels']
                })

        return devices


    def start_listening(self,device_index:Optional[int]=None)->bool:

        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size
            )

            self.is_listening = True
            self._stop_event.clear()

            logger.info('Microphone listening started')
            return True
        except Exception as e:
            logger.error(f"Failed to start microphone: {e}")
            return False

    def stop_listening(self)->None:
        self.is_listening = False
        self._stop_event.set()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        logger.info('Microphone listening stopped')

    def read_audio_chunk(self) -> Optional[bytes]:
        if not self.stream or not self.is_listening:
            return None
        try:
            return self.stream.read(self.chunk_size,exception_on_overflow=False)
        except Exception as e:
            logger.error(f"Error reading audio: {e}")
            return None

    def stream_audio(self)->Generator[bytes,None,None]:

        while self.is_listening and not self._stop_event.is_set():
            chunk = self.read_audio_chunk()
            if chunk:
                yield chunk

    def record_audio(self,duration: float=5.0)->Optional[bytes]:

        if not self.stream:
            logger.error("Microphone not started")
            return None

        frames = []
        chunks_per_second = int(self.sample_rate/self.chunk_size)
        total_chunks = int(duration*chunks_per_second)

        for _ in range(total_chunks):
            if not self.is_listening:
                break
            chunk = self.read_audio_chunk()
            if chunk:
                frames.append(chunk)

        return b''.join(frames) if frames else None

    def __enter__(self):
        self.start_listening()
        return self

    def __exit__(self,exc_type,exc_val,exc_tb):
        self.stop_listening()


    def cleanup(self)->None:
        self.stop_listening()
        self.audio.terminate()

    