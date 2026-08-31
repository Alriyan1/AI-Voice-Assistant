import subprocess
from typing import Optional
from loguru import logger
from pydantic import BaseModel
import pyautogui

class MediaResult(BaseModel):
    success:bool
    message:str
    current_value:Optional[int]=None


class MediaTools:

    def __init__(self):
        pass

    def change_volume(self,level:int)->MediaResult:

        try:
            level = max(0,min(100,level))

            current = 0
            if level > current:
                for _ in range(level-current):
                    pyautogui.press('volumeup')
            elif level < current:
                for _ in range(current - level):
                    pyautogui.press('volumedown')

            logger.info(f"Volume changed to: {level}%")

            return MediaResult(
                success=True,
                message=f"Volume set to {level}%",
                current_value=level
            )
            
        except Exception as e:
            logger.error(f"Volume change failed: {e}")
            return MediaResult(
                success=False,
                message=f"Volume change failed: {str(e)}"
            )


    def mute_volume(self) -> MediaResult:
        
        try:
            pyautogui.press('volumemute')
            logger.info("Volume muted")
            
            return MediaResult(
                success=True,
                message="Volume muted"
            )
            
        except Exception as e:
            logger.error(f"Mute failed: {e}")
            return MediaResult(
                success=False,
                message=f"Mute failed: {str(e)}"
            )
    
    def increase_volume(self) -> MediaResult:
        
        try:
            pyautogui.press('volumeup')
            logger.info("Volume increased")
            
            return MediaResult(
                success=True,
                message="Volume increased"
            )
            
        except Exception as e:
            logger.error(f"Increase volume failed: {e}")
            return MediaResult(
                success=False,
                message=f"Increase volume failed: {str(e)}"
            )
    
    def decrease_volume(self) -> MediaResult:
        
        try:
            pyautogui.press('volumedown')
            logger.info("Volume decreased")
            
            return MediaResult(
                success=True,
                message="Volume decreased"
            )
            
        except Exception as e:
            logger.error(f"Decrease volume failed: {e}")
            return MediaResult(
                success=False,
                message=f"Decrease volume failed: {str(e)}"
            )
    
    def play_pause(self) -> MediaResult:
        
        try:
            pyautogui.press('playpause')
            logger.info("Play/pause toggled")
            
            return MediaResult(
                success=True,
                message="Play/pause toggled"
            )
            
        except Exception as e:
            logger.error(f"Play/pause failed: {e}")
            return MediaResult(
                success=False,
                message=f"Play/pause failed: {str(e)}"
            )
    
    def next_track(self) -> MediaResult:
        
        try:
            pyautogui.press('nexttrack')
            logger.info("Next track")
            
            return MediaResult(
                success=True,
                message="Next track"
            )
            
        except Exception as e:
            logger.error(f"Next track failed: {e}")
            return MediaResult(
                success=False,
                message=f"Next track failed: {str(e)}"
            )
    
    def previous_track(self) -> MediaResult:
        
        try:
            pyautogui.press('prevtrack')
            logger.info("Previous track")
            
            return MediaResult(
                success=True,
                message="Previous track"
            )
            
        except Exception as e:
            logger.error(f"Previous track failed: {e}")
            return MediaResult(
                success=False,
                message=f"Previous track failed: {str(e)}"
            )