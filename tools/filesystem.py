import shutil
import os
from pathlib import Path
from typing import Optional,List,Dict
from datetime import datetime,timedelta
from loguru import logger
from pydantic import BaseModel
from config.settings import settings


class FileOperationResult(BaseModel):

    success: bool
    message: str
    path: Optional[str] = None
    requires_confirmation: bool = False


class FilesystemTools:

    def __init__(self):
        self.protected_paths = [
            Path('C:\\Windows'),
            Path('C:\\Program Files'),
            Path('C:\\Program Files (x86)'),
            Path(os.environ.get('SYSTEMROOT', 'C:\\Windows'))
        ]

    def _is_protected_path(self,path:Path) -> bool:
        for protected in self.protected_paths:
            try:
                path.relative_to(protected)
                return True
            except ValueError:
                continue

        return False

    def _safe_path(self,path_str:str)->Optional[Path]:
        try:
            path = Path(path_str).expanduser().resolve()

            if self._is_protected_path(path):
                logger.warning(f"Attempted to access protected path: {path}")
                return None

            return path
        except Exception as e:
            logger.error(f"Invalid path: {e}")
            return None

    def search_files(
            self,
            pattern:str,
            search_path: Optional[str] = None,
            file_type: Optional[str] = None
    ) -> FileOperationResult:

        try:
            search_dir = Path(search_path) if search_path else Path.home()
            if not search_dir.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Search directory not found: {search_dir}"
                )

            matches = []

            for root,dirs,files in os.walk(search_dir):
                if root.replace(str(search_dir),'').count(os.sep)>5:
                    continue

                for file in files:
                    if pattern.lower() in file.lower():
                        if file_type and not file.lower().endswith(f".{file_type.lower()}"):
                            continue
                        matches.append(str(Path(root)/file))

                if len(matches)>=50:
                    break

            message = f"Found {len(matches)} file(s) matching '{pattern}'"
            if matches:
                message += f": {', '.join(matches[:5])}"
                if len(matches)>5:
                    message += f" and {len(matches)-5} more"

            return FileOperationResult(
                success=True,
                message=message,
                path=str(matches[0]) if matches else None
            )

        except Exception as e:
            logger.error(f"File search failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Search failed: {str(e)}"
            )

    def create_folder(self,folder_name:str,location: Optional[str] = None)->FileOperationResult:

        try:
            if location:
                parent = Path(location)
            else:
                parent = Path.home() / 'Desktop'

            if not parent.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Location not found: {location}"
                )

            new_folder = parent/folder_name

            if new_folder.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Folder already exists: {folder_name}"
                )

            new_folder.mkdir(parents=True)
            logger.info(f"Created folder: {new_folder}")

            return FileOperationResult(
                success=True,
                message=f'Created folder: {new_folder}',
                path=str(new_folder)
            )

        except Exception as e:
            logger.error(f"Folder creation failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Error creating folder: {str(e)}"
            )

    def create_file(self,file_name:str, content:str = '',location:Optional[str]=None)->FileOperationResult:

        try:
            if location:
                parent = Path(location)
            else:
                parent = Path.home() / 'Desktop'
            
            if not parent.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Location not found: {location}"
                )
            
            new_file = parent / file_name
            
            if new_file.exists():
                return FileOperationResult(
                    success=False,
                    message=f"File already exists: {file_name}"
                )

            with open(new_file,'w',encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Created file: {new_file}")

            return FileOperationResult(
                success=True,
                message=f"Created file: {new_file}",
                path=str(new_file)
            )

        except Exception as e:
            logger.error(f"File creation failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Error creating file: {str(e)}"
            )

    def rename_file(self,old_path:str,new_name:str)->FileOperationResult:

        try:
            old = Path(old_path)

            if not old.exists():
                return FileOperationResult(
                    success=False,
                    message=f"File not found: {old_path}"
                )

            new = old.parent/new_name

            if new.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Destination already exists: {new_name}"
                )

            old.rename(new)
            logger.info(f"Renamed: {old}->{new}")

            return FileOperationResult(
                success=True,
                message=f"Renamed to: {new_name}",
                path=str(new)
            )
            
        except Exception as e:
            logger.error(f"Rename failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Error renaming file: {str(e)}"
            )

    def move_file(self,source_path:str,destination_path:str)->FileOperationResult:

        try:
            source = Path(source_path)
            dest = Path(destination_path)

            if not source.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Source not found: {source_path}"
                )

            if dest.is_dir():
                dest = dest / source.name

            shutil.move(str(source),str(dest))
            logger.info(f"Moved: {source} -> {dest}")

            return FileOperationResult(
                success=True,
                message=f"Moved to: {dest}",
                path=str(dest)
            )

        except Exception as e:
            logger.error(f"Move failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Error moving file: {str(e)}"
            )

    def copy_file(self,source_path:str,destination_path:str)->FileOperationResult:

        try:
            source = Path(source_path)
            dest = Path(destination_path)
            
            if not source.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Source not found: {source_path}"
                )
            
            if dest.is_dir():
                dest = dest / source.name
            
            shutil.copy2(str(source), str(dest))
            logger.info(f"Copied: {source} -> {dest}")
            
            return FileOperationResult(
                success=True,
                message=f"Copied to: {dest}",
                path=str(dest)
            )
            
        except Exception as e:
            logger.error(f"Copy failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Error copying file: {str(e)}"
            )
        
    def delete_file(self,file_path:str,require_confirmation:bool=True)->FileOperationResult:

        try:
            path = Path(file_path)
            if not path.exists():
                return FileOperationResult(
                    success=False,
                    message=f"File not found: {file_path}"
                )

            if self._is_protected_path(path):
                return FileOperationResult(
                    success=False,
                    message='Cannot delete protected system file',
                    requires_confirmation=True
                )

            if require_confirmation and settings.require_confirmation_for_destructive:
                return FileOperationResult(
                    success=False,
                    message=f"Confirmation required to delete: {path}",
                    requires_confirmation=True
                )

            path.unlink()
            logger.info(f"Deleted: {path}")

            return FileOperationResult(
                success=True,
                message=f"Deleted: {file_path}"
            )
            
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Error deleting file: {str(e)}"
        )

    def read_file(self,file_path:str,max_lines:int=1000)->FileOperationResult:

        try:
            path = Path(file_path)

            if not path.exists():
                return FileOperationResult(
                    success=False,
                    message=f"File not found: {file_path}"
                )

            if not path.is_file():
                return FileOperationResult(
                    success=False,
                    message=f"Not a file: {file_path}"
                )

            with open(path,'r',encoding='utf-8',errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"... ({max_lines} lines max)")
                        break
                    lines.append(line.rstrip())

            content = '\n'.join(lines)

            logger.info(f"Read file: {path} ({len(lines)} lines)")

            return FileOperationResult(
                success=True,
                message=f"Read {len(lines)} lines from {file_path}",
                path=str(path)
            )

        except Exception as e:
            logger.error(f"Read failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Error reading file: {str(e)}"
            )


    def get_files_by_date(self,days:int=1,location: Optional[str]=None)->FileOperationResult:

        try:
            search_dir = Path(location) if location else Path.home()
            cutoff = datetime.now() - timedelta(days=days)

            matches = []

            for root,dirs,files in os.walk(search_dir):
                if root.replace(str(search_dir),'').count(os.sep)>3:
                    continue

                for file in files:
                    file_path = Path(root)/file
                    try:
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if mtime>cutoff:
                            matches.append(str(file_path))
                    except (OSError,ValueError):
                        continue

                if len(matches) >= 50:
                    break

            message = f"Found {len(matches)} file(s) modified in last {days} day(s)"

            if matches:
                message += f": {', '.join(matches[:5])}"

            return FileOperationResult(
                success=True,
                message=message,
                path=str(matches[0]) if matches else None
            )
            
        except Exception as e:
            logger.error(f"Date-based search failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Search failed: {str(e)}"
            )