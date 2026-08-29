import subprocess
import psutil
from typing import Optional,List,Dict
from pathlib import Path
from loguru import logger
from pydantic import BaseModel,Field
from config.settings import settings

class ApplicationResult(BaseModel):
    success: bool
    message: str
    process_id: Optional[int] = None
    application_name: Optional[str] = None

class ApplicationTools:
    def __init__(self):
        self.allowed_apps = settings.allowed_applications
        self.app_paths = {
            'chrome':settings.chrome_path,
            'vscode':settings.vscode_path,
            'notepad':settings.notepad_path,
            'edge': r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            'firefox': r"C:\Program Files\Mozilla Firefox\firefox.exe"

        }

    def _normalize_app_name(self,name:str)->str:
        name = name.lower().strip()
        mappings = {
            'google chrome': 'chrome',
            'chrome': 'chrome',
            'vs code': 'vscode',
            'visual studio code': 'vscode',
            'code': 'vscode',
            'notepad': 'notepad',
            'edge': 'edge',
            'microsoft edge': 'edge',
            'firefox': 'firefox'
        }

        return mappings.get(name,name)

    def open_application(self,app_name:str,arguments:Optional[List[str]]=None) -> ApplicationResult:

        try:
            normalize_name = self._normalize_app_name(app_name)

            if normalize_name not in self.app_paths:
                return ApplicationResult(
                    success=False,
                    message=f"Unknowm application: {app_name}"
                )

            app_path = self.app_paths[normalize_name]

            if not Path(app_path).exists():
                return ApplicationResult(
                    success=False,
                    message=f"Application not found: {app_name}"
                )

            cmd = [app_path]
            if arguments:
                cmd.extend(arguments)

            process = subprocess.Popen(cmd)
            logger.info(f"Opened Application: {app_name} (PID:{process.pid})")

            return ApplicationResult(
                success=True,
                message=f"Successfully opened {app_name}",
                process_id=process.pid,
                application_name=normalize_name
            )

        except Exception as e:
            logger.error(f"Failed to open application: {e}")
            return ApplicationResult(
                success=False,
                message=f"Error opening {app_name}: {str(e)}"
            )

    def close_application(self,app_name:str) -> ApplicationResult:

        try:
            normalized_name = self._normalize_app_name(app_name)
            closed_count = 0

            for proc in psutil.process_iter(['name','pid']):
                try:
                    proc_name = proc.info['name'].lower() if proc.info['name'] else ''

                    if normalized_name in proc_name or proc_name in normalized_name:
                        proc.terminate()
                        closed_count += 1
                        logger.info(f"Closed process: {proc_name} (PID: {proc.info['pid']})")

                except (psutil.NoSuchProcess,psutil.AccessDenied):
                    continue

            if closed_count > 0:
                return ApplicationResult(
                    success=True,
                    message=f"Closed {closed_count} instance(s) of {app_name}"
                )
            else:
                return ApplicationResult(
                    success=False,
                    message=f"No running instances of {app_name} found"
                )

        except Exception as e:
            logger.error(f"Failed to close application: {e}")
            return ApplicationResult(
                success=False,
                message=f"Error closing {app_name}: {str(e)}"
            )

    def get_running_application(self) -> List[Dict]:

        try:
            apps = []
            for proc in psutil.process_iter(['name','pid','status']):
                try:
                    apps.append({
                        'name':proc.info['name'],
                        'pid':proc.info['pid'],
                        'status':proc.info['status']
                    })
                except (psutil.NoSuchProcess,psutil.AccessDenied):
                    continue

            logger.info(f"Found {len(apps)} running processes")
            return apps
        except Exception as e:
            logger.error(f"Failed to get running applications: {e}")
            return []

    def is_application_running(self,app_name:str)->bool:
        normalized_name = self._normalize_app_name(app_name)

        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower() if proc.info['name'] else ''

                if normalized_name in proc_name or proc_name in normalized_name:
                    return True
            except (psutil.NoSuchProcess,psutil.AccessDenied):
                continue

        return False