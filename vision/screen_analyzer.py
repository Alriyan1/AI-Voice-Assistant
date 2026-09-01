from PIL import Image
from typing import Optional,List,Dict,Tuple
from loguru import logger
from groq import Groq
from config.settings import settings
import base64
import io

class ScreenAnalyzer:

    def __init__(self,model:str="llama-3.2-90b-vision-preview"):

        self.model = model
        self.client = Groq(api_key=settings.groq_api_key)

    def _image_to_base64(self,image:Image.Image)->str:
        buffer = io.BytesIO()
        image.save(buffer,format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def analyzer_screen(
            self,
            image:Image.Image,
            query:str="Describe what's on this screen"
    )->Optional[str]:

        try:
            base64_image = self._image_to_base64(image)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": query
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1024
            )

            analysis = response.choices[0].message.content
            logger.info(f"Screen analysis completed: {analysis[:100]}...")
            return analysis

        except Exception as e:
            logger.error(f"Screen analysis failed: {e}")
            return None

    def find_element(
            self,
            image:Image.Image,
            element_description:str
    )-> Optional[Dict]:

        try:

            query = f"""Find the following UI element: {element_description}
            
Respond in JSON format:
{{
    "found": true/false,
    "description": "what you found",
    "coordinates": {{
        "x": center_x,
        "y": center_y
    }},
    "confidence": 0.0-1.0
}}"""

            base64_image = self._image_to_base64(image)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=512
            )

            analysis = response.choices[0].message.content
            logger.info(f"Element search: {element_description}")
            
            return {
                'found': True,
                'description': element_description,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Element search failed: {e}")
            return None

    def locate_text(
            self,
            image:Image.Image,
            text_pattern: str
    )-> Optional[List[Tuple[int,int]]]:

        try:
            query = f"""Locate all instances of text matching: "{text_pattern}"
            
For each instance, provide coordinates as [x, y].
Return as JSON array: [[x1, y1], [x2, y2], ...]"""
            
            base64_image = self._image_to_base64(image)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=512
            )
            
            logger.info(f"Text location: {text_pattern}")
            return {'analysis': response.choices[0].message.content}
            
        except Exception as e:
            logger.error(f"Text location failed: {e}")
            return None

    def get_ui_elements(self,image:Image.Image)->Optional[List[Dict]]:

        try:
            query = """Identify all interactive UI elements on this screen:
- Buttons
- Text fields
- Menus
- Icons
- Links

For each element, provide:
- Type
- Label/Text
- Approximate location (top-left, center, bottom-right, etc.)

Return as JSON array."""
            
            base64_image = self._image_to_base64(image)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2048
            )
            
            logger.info("UI element extraction completed")
            return {'elements': response.choices[0].message.content}
            
        except Exception as e:
            logger.error(f"UI extraction failed: {e}")
            return None