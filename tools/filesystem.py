import shutil
import os
import difflib
import re
from xml.sax.saxutils import escape
from pathlib import Path
from typing import Optional,List,Dict
from datetime import datetime,timedelta
from loguru import logger
from pydantic import BaseModel
from config.settings import settings

DEFAULT_STORAGE_PATH = Path('E:/')


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

    @staticmethod
    def _normalise_filename(value: str) -> str:
        return re.sub(r'[^a-z0-9]+', '', value.lower())

    @staticmethod
    def _location_candidates(location: Optional[str]) -> List[Path]:
        if not location:
            return [Path.home()]

        cleaned = location.strip().strip('"')
        cleaned = re.sub(
            r'(?i)^C:[/\\]Users[/\\]Username[/\\]Desktop',
            'C:/Users/Public/Desktop',
            cleaned
        )
        location_name = cleaned.lower().replace('\\', '/').strip('/')
        if location_name in {'desktop', 'the desktop'}:
            return [
                Path('C:/Users/Public/Desktop'),
                Path.home() / 'Desktop',
                Path.home() / 'OneDrive' / 'Desktop',
            ]

        path = Path(cleaned).expanduser()
        if not path.exists() and path.name.lower() == 'desktop':
            return [
                Path('C:/Users/Public/Desktop'),
                Path.home() / 'Desktop',
                Path.home() / 'OneDrive' / 'Desktop',
            ]
        return [path]

    @staticmethod
    def _resolve_file_path(file_path: str) -> Path:
        cleaned = file_path.strip().strip('"')
        cleaned = re.sub(r'[/\\]+', lambda _: os.sep, cleaned)
        cleaned = re.sub(
            r'(?i)^C:[/\\]Users[/\\]Username[/\\]Desktop',
            'C:/Users/Public/Desktop',
            cleaned
        )
        if cleaned.lower().startswith('desktop' + os.sep) or cleaned.lower().startswith('desktop/'):
            cleaned = str(Path('C:/Users/Public') / cleaned)
        return Path(cleaned).expanduser()

    def _find_best_file(
            self,
            query: str,
            search_dirs: List[Path],
            file_type: Optional[str] = None
    ) -> Optional[Path]:
        query_name = Path(query).stem
        normalised_query = self._normalise_filename(query_name)
        candidates = []

        for search_dir in search_dirs:
            for path in search_dir.rglob('*'):
                if not path.is_file():
                    continue
                if file_type and path.suffix.lower() != f'.{file_type.lower().lstrip(".")}':
                    continue
                candidate_name = self._normalise_filename(path.stem)
                similarity = difflib.SequenceMatcher(
                    None, normalised_query, candidate_name
                ).ratio()
                if normalised_query and normalised_query in candidate_name:
                    similarity = max(similarity, 0.85)
                candidates.append((similarity, path))

        if not candidates:
            return None

        similarity, path = max(candidates, key=lambda item: item[0])
        return path if similarity >= 0.55 else None

    def search_files(
            self,
            pattern:str,
            search_path: Optional[str] = None,
            file_type: Optional[str] = None
    ) -> FileOperationResult:

        try:
            search_dirs = [path for path in self._location_candidates(search_path) if path.exists()]
            if not search_dirs:
                return FileOperationResult(
                    success=False,
                    message=f"Search directory not found: {search_path or Path.home()}"
                )

            best_match = self._find_best_file(pattern, search_dirs, file_type)
            if not best_match:
                return FileOperationResult(
                    success=False,
                    message=f"File not found: {pattern}"
                )

            message = f"Found the most similar file: {best_match}"

            return FileOperationResult(
                success=True,
                message=message,
                path=str(best_match)
            )

        except Exception as e:
            logger.error(f"File search failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Search failed: {str(e)}"
            )

    def find_best_file(
            self,
            query: str,
            location: Optional[str] = None,
            file_type: Optional[str] = None
    ) -> FileOperationResult:
        search_dirs = [
            path for path in self._location_candidates(location or 'Desktop')
            if path.exists()
        ]
        if not search_dirs:
            return FileOperationResult(
                success=False,
                message='Desktop location not found'
            )

        best_match = self._find_best_file(query, search_dirs, file_type)
        if not best_match:
            return FileOperationResult(
                success=False,
                message=f"File not found: {query}"
            )

        return FileOperationResult(
            success=True,
            message=f"Found the most similar file: {best_match}",
            path=str(best_match)
        )

    def create_folder(self,folder_name:str,location: Optional[str] = None)->FileOperationResult:

        try:
            if location:
                parent = Path(location)
            else:
                parent = DEFAULT_STORAGE_PATH

            if not parent.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Location not found: {parent}"
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
                parent = DEFAULT_STORAGE_PATH
            
            if not parent.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Location not found: {parent}"
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

    def create_pdf(
            self,
            file_name: str,
            content: str,
            location: Optional[str] = None
    ) -> FileOperationResult:
        """Create a readable PDF directly without keyboard or application automation."""
        try:
            from reportlab.lib.pagesizes import LETTER
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

            if not file_name.lower().endswith('.pdf'):
                file_name += '.pdf'

            requested_location = (location or '').replace('C:\\Users\\Username', str(Path.home()))
            if requested_location.lower().strip() in {'desktop', 'the desktop'}:
                parent = Path('C:/Users/Public/Desktop')
            else:
                parent = (
                    Path(requested_location).expanduser()
                    if requested_location
                    else Path('C:/Users/Public/Desktop')
                )

            if not parent.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Location not found: {parent}"
                )

            output_path = parent / file_name
            styles = getSampleStyleSheet()
            document = SimpleDocTemplate(
                str(output_path),
                pagesize=LETTER,
                rightMargin=inch,
                leftMargin=inch,
                topMargin=inch,
                bottomMargin=inch,
            )
            story = []
            for paragraph in content.split('\n'):
                if paragraph.strip():
                    story.append(Paragraph(escape(paragraph), styles['BodyText']))
                    story.append(Spacer(1, 0.15 * inch))
            document.build(story)

            logger.info(f"Created PDF: {output_path}")
            return FileOperationResult(
                success=True,
                message=f"Created PDF: {output_path}",
                path=str(output_path)
            )

        except Exception as e:
            logger.error(f"PDF creation failed: {e}")
            return FileOperationResult(
                success=False,
                message=f"Error creating PDF: {str(e)}"
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
            path = self._resolve_file_path(file_path)
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

    def delete_matching_file(
            self,
            query: str,
            location: Optional[str] = None,
            require_confirmation: bool = True
    ) -> FileOperationResult:
        """Find one matching file in a user location and delete it after approval."""
        search_dirs = [
            path for path in self._location_candidates(location or 'Desktop')
            if path.exists()
        ]
        if not search_dirs:
            return FileOperationResult(
                success=False,
                message='Desktop location not found'
            )

        best_match = self._find_best_file(query, search_dirs)
        if not best_match:
            return FileOperationResult(
                success=False,
                message=f"File not found: {query}"
            )

        return self.delete_file(str(best_match), require_confirmation=require_confirmation)

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