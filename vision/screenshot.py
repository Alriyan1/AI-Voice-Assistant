import pyautogui
from PIL import Image
from typing import Optional,Tuple
from pathlib import Path
from loguru import logger
import io

class ScreenshotManager:

    def __init__(self):
        self.temp_dir = Path('./temp/screenshots')
        self.temp_dir.mkdir(parents=True,exist_ok=True)


    def capture_screen(self,region:Optional[Tuple[int,int,int,int]]=None)->Optional[Image.Image]:

        try:
            if region:
                screenshot = pyautogui.screenshot(region=region)
                logger.info(f"Captured screenshot region: {region}")

            else:
                screenshot = pyautogui.screenshot()
                logger.info('Captured full screenshot')

            return screenshot

        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

    def save_screenshot(self,image:Image.Image,filename:Optional[str]=None)->Optional[str]:

        try:
            if filename is None:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"

            filepath = self.temp_dir/filename
            image.save(filepath,'PNG')

            logger.info(f"Saved screenshot: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Screenshot save failed: {e}")
            return None

    def capture_and_save(self,region:Optional[Tuple[int,int,int,int]]=None)->Optional[str]:

        screenshot = self.capture_screen(region)
        if screenshot:
            return self.save_screenshot(screenshot)

        return None

    def get_screen_size(self)->Tuple[int,int]:

        try:
            width,height = pyautogui.size()
            logger.info(f"Screen size: {width}x{height}")
            return (width,height)

        except Exception as e:
            logger.error(f"Get screen size failed: {e}")
            return (1920,1080)

    def image_to_bytes(self,image:Image.Image,format:str='PNG')->Optional[bytes]:

        try:
            buffer = io.BytesIO()
            image.save(buffer,format=format)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Image to bytes failed: {e}")
            return None


    def bytes_to_image(self,image_bytes:bytes)->Optional[Image.Image]:

        try:
            buffer = io.BytesIO(image_bytes)
            return Image.open(buffer)

        except Exception as e:
            logger.error(f"Bytes to image failed: {e}")
            return None
    