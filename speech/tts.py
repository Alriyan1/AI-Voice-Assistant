import edge_tts
import asyncio
from typing import Optional,AsyncGenerator
from pathlib import Path
import tempfile
from loguru import logger
from config.settings import settings
import pygame

class TextToSpeech:

    def __init__(self,voice:str=None):

        self.voice = voice or settings.tts_voice
        self.temp_dir = Path(tempfile.gettempdir())/'tts_cache'
        self.temp_dir.mkdir(parents=True,exist_ok=True)
        pygame.mixer.init()

    async def generate_speech(self,text:str)->Optional[bytes]:
        try:
            communicate = edge_tts.Communicate(text,self.voice)
            audio_data = b''

            async for chunk in communicate.stream():
                if chunk['type'] == 'audio':
                    audio_data += chunk['data']

            logger.info(f"Generated speech for: {text[:50]}...")
            return audio_data

        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return None

    async def save_speech(self,text:str,output_path:str)->Optional[str]:
        try:
            communicate = edge_tts.Communicate(text,self.voice)
            await communicate.save(output_path)
            logger.info(f"Saved speech to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f'Failed to save speech: {e}')
            return None


    def play_audio(self,audio_data:bytes)->bool:
        try:
            temp_file = self.temp_dir/'temp_audio.mp3'
            with open(temp_file,'wb') as f:
                f.write(audio_data)

            pygame.mixer.music.load(str(temp_file))
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            return True

        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
            return False


    async def speak(self,text:str)->bool:
        try:
            audio_data = await self.generate_speech(text)
            if audio_data:
                return self.play_audio(audio_data)
            return False
        except Exception as e:
            logger.error(f"Speak failed: {e}")
            return False


    def list_voices(self)->list:
        voices = [
            "en-US-EmmaMultilingualNeural",
            "en-US-AndrewMultilingualNeural",
            "en-US-BrianNeural",
            "en-US-JennyNeural",
            "en-GB-SoniaNeural",
            "en-GB-RyanNeural"
        ]
        return voices