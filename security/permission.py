from typing import Set,Optional,List
from pydantic import BaseModel
from config.settings import settings
from enum import Enum
from loguru import logger

class ActionRiskLevel(Enum):

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class PermissionResult(BaseModel):
    allowed: bool
    requires_confirmation: bool
    reason:str
    risk_level: ActionRiskLevel

class PermissionManager:

    def __init__(self):

        self.allowed_applications = set(settings.allowed_applications)

        self.action_risk_levels = {
            # Low risk - informational
            'get_cpu_usage': ActionRiskLevel.LOW,
            'get_memory_usage': ActionRiskLevel.LOW,
            'get_system_information': ActionRiskLevel.LOW,
            'get_running_applications': ActionRiskLevel.LOW,
            'search_files': ActionRiskLevel.LOW,
            
            # Medium risk - modifications
            'open_application': ActionRiskLevel.MEDIUM,
            'close_application': ActionRiskLevel.MEDIUM,
            'create_folder': ActionRiskLevel.MEDIUM,
            'create_file': ActionRiskLevel.MEDIUM,
            'type_text': ActionRiskLevel.MEDIUM,
            'navigate_to': ActionRiskLevel.MEDIUM,
            
            # High risk - destructive
            'delete_file': ActionRiskLevel.HIGH,
            'move_file': ActionRiskLevel.HIGH,
            'rename_file': ActionRiskLevel.HIGH,
            'shutdown_system': ActionRiskLevel.CRITICAL,
            'restart_system': ActionRiskLevel.CRITICAL,
            'lock_system': ActionRiskLevel.HIGH,
        }

        #Actions that always require confirmation
        self.confirmation_required = {
            'delete_file',
            'shutdown_system',
            'restart_system',
            'lock_system',
            'move_file',
            'run_allowed_program'
        }

    def check_permission(
            self,
            action:str,
            target: Optional[str]=None
    )->PermissionResult:

        risk_level = self.action_risk_levels.get(action,ActionRiskLevel.MEDIUM)

        requires_confirmation = (
            action in self.confirmation_required or 
            risk_level in [ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL]
        )

        if action == 'open_application' and target:
            app_name = target.lower().strip()
            if app_name not in self.allowed_applications:
                return PermissionResult(
                    allowed=False,
                    requires_confirmation=False,
                    reason=f"Application '{target}' is not in allowed list",
                    risk_level=ActionRiskLevel.MEDIUM
                )

        if action in ['delete_file', 'move_file'] and target:
            if self._is_protected_path(target):
                return PermissionResult(
                    allowed=False,
                    requires_confirmation=True,
                    reason="Cannot modify protected system files",
                    risk_level=ActionRiskLevel.CRITICAL
                )
        
        return PermissionResult(
            allowed=True,
            requires_confirmation=requires_confirmation,
            reason="Action permitted",
            risk_level=risk_level
        )

    def _is_protected_path(self,path:str)->bool:

        protected = [
            'C:\\Windows',
            'C:\\Program Files',
            'C:\\Program Files (x86)',
            'C:\\Users\\All Users'
        ]

        path_lower = path.lower()
        return any(p.lower() in path_lower for p in protected)

    def add_allowed_application(self,app_name:str)->bool:

        try:
            self.allowed_applications.add(app_name.lower())
            logger.info(f"Added allowed application: {app_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add application: {e}")
            return False

    def remove_allowed_application(self,app_name:str)->bool:

        try:
            self.allowed_applications.discard(app_name.lower())
            logger.info(f"Removed allowed application: {app_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove application: {e}")
            return False


    def get_allowed_applications(self) -> Set[str]:

        return self.allowed_applications.copy()

    def log_action(
            self,
            action: str,
            target: Optional[str],
            result: bool,
            user_command: str
    )->None:

        logger.info(
            f"ACTION_LOG: {action} | target={target} |"
            f"result={result} | command={user_command}"
        )