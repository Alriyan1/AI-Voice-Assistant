import pyautogui
from typing import Optional,Tuple
from loguru import logger
from pydantic import BaseModel
import time

class MouseResult(BaseModel):
    success:bool
    message:str
    position: Optional[Tuple[int,int]]=None

class MouseTools:

    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

    def move_to(self,x:int,y:int,duration:float=0.5)->MouseResult:

        try:
            pyautogui.moveTo(x,y,duration=duration)
            logger.info(f"Moved to: ({x}, {y})")

            return MouseResult(
                success=True,
                message=f"Moved to ({x}, {y})",
                position=(x, y)
            )
            
        except Exception as e:
            logger.error(f"Move failed: {e}")
            return MouseResult(
                success=False,
                message=f"Move failed: {str(e)}"
            )

    def click(self,x:Optional[int]=None,y:Optional[int]=None,button:str='left')->MouseResult:
        try:
            if x is not None and y is not None:
                pyautogui.click(x=x,y=y,button=button)
                pos=(x,y)
            else:
                pyautogui.click(button=button)
                pos=pyautogui.position()

            logger.info(f"Clicked: {button} at {pos}")

            return MouseResult(
                success=True,
                message=f"Clicked {button} button",
                position=pos
            )

        except Exception as e:
            logger.error(f"Click failed: {e}")
            return MouseResult(
                success=False,
                message=f"Clicked failed: {str(e)}"
            )

    def double_click(self,x:Optional[int]=None,y:Optional[int]=None)->MouseResult:

        try:
            if x is not None and y is not None:
                pyautogui.doubleClick(x=x,y=y)
                pos = (x,y)

            else:
                pyautogui.doubleClick()
                pos = pyautogui.position()

            logger.info(f"Double-clicked at: {pos}")
            
            return MouseResult(
                success=True,
                message="Double-clicked",
                position=pos
            )
            
        except Exception as e:
            logger.error(f"Double-click failed: {e}")
            return MouseResult(
                success=False,
                message=f"Double-click failed: {str(e)}"
            )

    def scroll(self,amount:int,x:Optional[int]=None,y:Optional[int]=None)->MouseResult:

        try:
            if x is not None and y is not None:
                pyautogui.scroll(amount, x=x, y=y)
                pos = (x, y)
            else:
                pyautogui.scroll(amount)
                pos = pyautogui.position()
            
            logger.info(f"Scrolled: {amount} at {pos}")
            
            return MouseResult(
                success=True,
                message=f"Scrolled {amount}",
                position=pos
            )
            
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return MouseResult(
                success=False,
                message=f"Scroll failed: {str(e)}"
            )

    def get_position(self)->MouseResult:
        try:
            pos = pyautogui.position()
            logger.info(f"Mouse position: {pos}")
            
            return MouseResult(
                success=True,
                message=f"Position: {pos}",
                position=(pos.x, pos.y)
            )
            
        except Exception as e:
            logger.error(f"Get position failed: {e}")
            return MouseResult(
                success=False,
                message=f"Get position failed: {str(e)}"
            )

    def drag_to(self,x:int,y:int,duration:float=1.0)->MouseResult:

        try:
            pyautogui.dragTo(x, y, duration=duration)
            logger.info(f"Dragged to: ({x}, {y})")
            
            return MouseResult(
                success=True,
                message=f"Dragged to ({x}, {y})",
                position=(x, y)
            )
            
        except Exception as e:
            logger.error(f"Drag failed: {e}")
            return MouseResult(
                success=False,
                message=f"Drag failed: {str(e)}"
            )