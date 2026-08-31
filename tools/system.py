import psutil
import subprocess
from typing import Dict, List, Optional
from loguru import logger
from pydantic import BaseModel
from config.settings import settings

class SystemResult(BaseModel):
    success:bool
    message:str
    data:Optional[Dict] = None

class SystemTools:

    def __init__(self):
        pass

    def get_cpu_usage(self) -> SystemResult:
        try:
            usage = psutil.cpu_percent(interval=1)
            per_cpu = psutil.cpu_percent(interval=1,percpu=True)

            logger.info(f"CPU usage: {usage}%")

            return SystemResult(
                success=True,
                message=f"CPU usage: {usage}%",
                data={
                    'total': usage,
                    'per_cpu': per_cpu,
                    'cores': psutil.cpu_count()
                }
            )
            
        except Exception as e:
            logger.error(f"CPU usage check failed: {e}")
            return SystemResult(
                success=False,
                message=f"CPU check failed: {str(e)}"
            )


    def get_memory_usage(self) -> SystemResult:

        try:
            memory = psutil.virtual_memory()

            info = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'percent': memory.percent
            }

            logger.info(f"Memory usage: {memory.percent}%")
            
            return SystemResult(
                success=True,
                message=f"Memory usage: {memory.percent}% ({info['used_gb']}GB / {info['total_gb']}GB)",
                data=info
            )
            
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return SystemResult(
                success=False,
                message=f"Memory check failed: {str(e)}"
            )


    def get_disk_usage(self) -> SystemResult:
        
        try:
            disk = psutil.disk_usage('C:\\')
            
            info = {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent': disk.percent
            }
            
            logger.info(f"Disk usage: {disk.percent}%")
            
            return SystemResult(
                success=True,
                message=f"Disk usage: {disk.percent}% ({info['free_gb']}GB free)",
                data=info
            )
            
        except Exception as e:
            logger.error(f"Disk check failed: {e}")
            return SystemResult(
                success=False,
                message=f"Disk check failed: {str(e)}"
            )
    
    def get_system_information(self) -> SystemResult:
        
        try:
            import platform
            
            info = {
                'system': platform.system(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'boot_time': psutil.boot_time(),
                'uptime_seconds': psutil.boot_time()
            }
            
            # Calculate uptime
            import datetime
            boot = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.datetime.now() - boot
            
            logger.info(f"System info retrieved")
            
            return SystemResult(
                success=True,
                message=f"System: {info['system']} {info['version']}, Uptime: {uptime}",
                data=info
            )
            
        except Exception as e:
            logger.error(f"System info failed: {e}")
            return SystemResult(
                success=False,
                message=f"System info failed: {str(e)}"
            )

    def get_running_processes(self,limit:int=20)->SystemResult:

        try:
            processes = []
            for proc in psutil.process_iter(['pid','name','cpu_percent','memory_percent']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': proc.info['cpu_percent'] or 0,
                        'memory': proc.info['memory_percent'] or 0
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            processes.sort(key=lambda x:x['memory'],reverse=True)
            top_processes = processes[:limit]

            logger.info(f"Retrieved {len(top_processes)} processes")
            
            return SystemResult(
                success=True,
                message=f"Top {len(top_processes)} processes by memory usage",
                data={'processes': top_processes}
            )
            
        except Exception as e:
            logger.error(f"Process list failed: {e}")
            return SystemResult(
                success=False,
                message=f"Process list failed: {str(e)}"
            )

    def shutdown_system(self,require_confirmation:bool=True) -> SystemResult:

        try:
            if require_confirmation and settings.require_confirmation_for_destructive:
                return SystemResult(
                    success=False,
                    message="Confirmation required to shutdown computer",
                    data={'requires_confirmation': True}
                )

            subprocess.run(['shutdown', '/s', '/t', '0'], check=True)

            logger.warning("System shutdown initiated")
            
            return SystemResult(
                success=True,
                message="System shutting down"
            )
            
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            return SystemResult(
                success=False,
                message=f"Shutdown failed: {str(e)}"
            )

    def restart_system(self,require_confirmation:bool=True)->SystemResult:

        try:
            if require_confirmation and settings.require_confirmation_for_destructive:
                return SystemResult(
                    success=False,
                    message="Confirmation required to restart computer",
                    data={'requires_confirmation': True}
                )
            
            subprocess.run(['shutdown', '/r', '/t', '0'], check=True)
            
            logger.warning("System restart initiated")
            
            return SystemResult(
                success=True,
                message="System restarting"
            )
            
        except Exception as e:
            logger.error(f"Restart failed: {e}")
            return SystemResult(
                success=False,
                message=f"Restart failed: {str(e)}"
            )

    def lock_system(self)->SystemResult:
        try:
            subprocess.run(['rundll32', 'user32.dll,LockWorkStation'], check=True)
            
            logger.info("System locked")
            
            return SystemResult(
                success=True,
                message="System locked"
            )
            
        except Exception as e:
            logger.error(f"Lock failed: {e}")
            return SystemResult(
                success=False,
                message=f"Lock failed: {str(e)}"
            )