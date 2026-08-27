from groq import Groq
from typing import Optional,List
from pathlib import Path
import tempfile
import wave 
from loguru import logger
from config.settings import settings


class SpeechToText:
    def __init__(self,model:str=None):
        self.model = model or settings.stt_model
        self.client = Groq(api_key=settings.groq_api_key)
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.flac']

    def audio_bytes_to_wav(self,audio_data:bytes,sample_rate:int=16000)->bytes:

        import io
        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer,'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data)

            return wav_buffer.getvalue()

    def transcribe_audio(self,audio_data:bytes,sample_rate:int=16000)->Optional[str]:

        try:
            wav_data = self.audio_bytes_to_wav(audio_data,sample_rate)

            with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as tmp_file:
                tmp_file.write(wav_data)
                tmp_path = tmp_file.name

            try:
                with open(tmp_file,'rb') as audio_file:
                    transcription = self.client.audio.transcriptions.create(
                        file=audio_file,
                        model='whisper-large-v3',
                        response_format='text',
                        language='en'
                    )

                text = transcription.strip()
                logger.info(f"Transcribed: {text[:100]}..." if len(text)>100 else f"Transcribed: {text}")
                return text
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"STT transcription failed: {e}")
            return None

    def transcribe_file(self,file_path:str)->Optional[str]:

        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Audio file not found: {file_path}")
                return None

            if path.suffix.lower() not in self.supported_formats:
                logger.error(f"Unsupported audio format: {path.suffix}")
                return None

            with open(path,'rb') as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model=self.model,
                    response_format='text',
                    language='en'
                )

            logger.info(f"Transcribed file: {file_path}")
            return transcription.strip()

        except Exception as e:
            logger.error(f'File transcription failed: {e}')
            return None

    def transcribe_streaming(
            self,
            audio_chunks: List[bytes],
            sample_rate: int = 16000
    ) -> Optional[str]:

        if not audio_chunks:
            return None

        combined_audio = b''.join(audio_chunks)
        return self.transcribe_audio(combined_audio,sample_rate)