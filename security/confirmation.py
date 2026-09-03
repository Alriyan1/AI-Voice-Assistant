from typing import Optional,Callable
from loguru import logger
import asyncio

class ConfirmationManager:

    def __init__(self):
        self.pending_confirmations = {}
        self.confirmation_timeout = 30 # second


    async def request_confirmation(
            self,
            action: str,
            description: str,
            callback: Optional[Callable] = None
    )-> bool:

        try:
            import uuid
            confirmation_id = str(uuid.uuid4())

            message = f"""
            ⚠️  **Confirmation Required**

            Action: {action}
            Description: {description}

            Do you want to proceed? (yes/no)
            """

            logger.warning(f"Confirmation requested: {action} - {description}")

            self.pending_confirmations[confirmation_id] = {
                'action': action,
                'description': description,
                'callback': callback,
                'timestamp': asyncio.get_event_loop().time()
            }

            print(message)

            return False

        except Exception as e:
            logger.error(f"Confirmation request failed: {e}")
            return False

    def confirm(self,confirmation_id: str)->bool:

        try:
            if confirmation_id not in self.pending_confirmations:
                logger.error(f"Unknown confirmation ID: {confirmation_id}")
                return False

            confirmation = self.pending_confirmations[confirmation_id]

            current_time = asyncio.get_event_loop().time()
            if current_time - confirmation['timestamp']>self.confirmation_timeout:
                logger.error(f"Confirmation expired: {confirmation_id}")
                del self.pending_confirmations[confirmation_id]
                return False

            if confirmation['callback']:
                confirmation['callback']()

            del self.pending_confirmations[confirmation_id]

            logger.info(f"Confirmation approved: {confirmation['action']}")
            return True

        except Exception as e:
            logger.error(f"Confirmation failed: {e}")
            return False

    def deny(self,confirmation_id: str)->bool:

        try:
            if confirmation_id in self.pending_confirmations:
                del self.pending_confirmations[confirmation_id]
                logger.info(f"Confirmation denied: {confirmation_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Confirmation denied failed: {e}")
            return False


    def get_pending_confirmations(self) -> list:

        return list(self.pending_confirmations.values())

    def cleaned_expired(self)->int:

        try:
            current_time = asyncio.get_event_loop().time()
            expired = []

            for conf_id, conf in self.pending_confirmations.items():
                if current_time - conf['timestamp'] > self.confirmation_timeout:
                    expired.append(conf_id)

            for conf_id in expired:
                del self.pending_confirmations[conf_id]

            logger.info(f"Cleaned up {len(expired)} expired confirmations")
            return len(expired)

        except Exception as e:
            logger.error(f"Confirmation cleaned failed: {e}")
            return 0