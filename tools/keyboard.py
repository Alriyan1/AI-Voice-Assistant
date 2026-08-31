import pyautogui
import keyboard
from typing import Optional,List
from loguru import logger
from pydantic import BaseModel
import time

class KeyboardResult(BaseModel):
    success:bool
    message:str


class KeyboardTools:
    def __init__(self):
        pyautogui.FAILSAFE = True

    def type_text(self,text:str,interval:float=0.05)->KeyboardResult:

        try:
            pyautogui.typewrite(text,interval=interval)
            logger.info(f"Typed: {text[:50]}...")

            return KeyboardResult(
                success=True,
                message=f"Typed: {text}"
            )

        except Exception as e:
            logger.error(f"Type failed: {e}")
            return KeyboardResult(
                success=False,
                message=f"Type failed: {str(e)}"
            )

    def press_key(self, key: str) -> KeyboardResult:
        
        try:
            pyautogui.press(key)
            logger.info(f"Pressed key: {key}")
            
            return KeyboardResult(
                success=True,
                message=f"Pressed: {key}"
            )
            
        except Exception as e:
            logger.error(f"Key press failed: {e}")
            return KeyboardResult(
                success=False,
                message=f"Key press failed: {str(e)}"
            )
    
    def press_keys(self, keys: List[str]) -> KeyboardResult:
        
        try:
            for key in keys:
                pyautogui.press(key)
                time.sleep(0.05)
            
            logger.info(f"Pressed keys: {keys}")
            
            return KeyboardResult(
                success=True,
                message=f"Pressed: {', '.join(keys)}"
            )
            
        except Exception as e:
            logger.error(f"Key sequence failed: {e}")
            return KeyboardResult(
                success=False,
                message=f"Key sequence failed: {str(e)}"
            )
    
    def hotkey(self, *keys: str) -> KeyboardResult:
        
        try:
            pyautogui.hotkey(*keys)
            logger.info(f"Hotkey: {'+'.join(keys)}")
            
            return KeyboardResult(
                success=True,
                message=f"Pressed: {'+'.join(keys)}"
            )
            
        except Exception as e:
            logger.error(f"Hotkey failed: {e}")
            return KeyboardResult(
                success=False,
                message=f"Hotkey failed: {str(e)}"
            )
    
    def key_down(self, key: str) -> KeyboardResult:
        
        try:
            pyautogui.keyDown(key)
            logger.info(f"Key down: {key}")
            
            return KeyboardResult(
                success=True,
                message=f"Holding: {key}"
            )
            
        except Exception as e:
            logger.error(f"Key down failed: {e}")
            return KeyboardResult(
                success=False,
                message=f"Key down failed: {str(e)}"
            )
    
    def key_up(self, key: str) -> KeyboardResult:
        
        try:
            pyautogui.keyUp(key)
            logger.info(f"Key up: {key}")
            
            return KeyboardResult(
                success=True,
                message=f"Released: {key}"
            )
            
        except Exception as e:
            logger.error(f"Key up failed: {e}")
            return KeyboardResult(
                success=False,
                message=f"Key up failed: {str(e)}"
            )