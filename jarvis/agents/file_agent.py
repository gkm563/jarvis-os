"""
File System Agent (FR-4) for JARVIS OS.
Provides safe filesystem CRUD operations, folder organization, SHA-256 duplicate detection, and versioned backups.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from jarvis.agents.base import AbstractAgent
from jarvis.core.models import AgentAction, ExecutionResult
from jarvis.config.settings import settings
from jarvis.utils.logger import get_logger

logger = get_logger("FileAgent")


class FileSystemAgent(AbstractAgent):
    """
    File System Agent implementing safe file management operations with safety guardrails.
    """

    @property
    def name(self) -> str:
        return "file_agent"

    @property
    def description(self) -> str:
        return "Manages local file system operations, duplicate file detection, versioned backups, and safe directory cleanup."

    @property
    def capabilities(self) -> List[str]:
        return [
            "read_file",
            "write_file",
            "delete_file",
            "organize_folder",
            "duplicate_scan",
            "backup_file",
        ]

    async def execute(self, action: AgentAction) -> ExecutionResult:
        """Executes file agent action."""
        if not await self.validate_action(action):
            return ExecutionResult(success=False, error_message=f"Unsupported action: {action.action_type}")

        action_type = action.action_type
        params = action.parameters

        try:
            if action_type == "read_file":
                filepath = params.get("filepath", "")
                return await self._read_file(filepath)

            elif action_type == "write_file":
                filepath = params.get("filepath", "")
                content = params.get("content", "")
                return await self._write_file(filepath, content)

            elif action_type == "delete_file":
                files = params.get("files", [params.get("filepath")])
                return await self._delete_files([f for f in files if f])

            elif action_type == "organize_folder":
                target_dir = params.get("target_path", "./Downloads")
                return await self._organize_folder(target_dir)

            elif action_type == "duplicate_scan":
                target_dir = params.get("target_path", ".")
                return await self._scan_duplicates(target_dir)

            elif action_type == "backup_file":
                filepath = params.get("filepath", "")
                return await self._backup_file(filepath)

            return ExecutionResult(success=False, error_message=f"Unhandled action type '{action_type}'")

        except Exception as e:
            logger.error(f"File Agent action '{action_type}' failed: {str(e)}")
            return ExecutionResult(success=False, error_message=str(e))

    async def _read_file(self, filepath: str) -> ExecutionResult:
        """Reads file contents."""
        path = Path(filepath)
        if not path.exists():
            return ExecutionResult(success=False, error_message=f"File not found: {filepath}")
        content = path.read_text(encoding="utf-8", errors="ignore")
        return ExecutionResult(success=True, data={"filepath": filepath, "content": content, "size_bytes": path.stat().st_size})

    async def _write_file(self, filepath: str, content: str) -> ExecutionResult:
        """Writes content to file, creating parent directories if needed."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Create a versioned backup if file already exists
        if path.exists():
            await self._backup_file(filepath)
        path.write_text(content, encoding="utf-8")
        logger.info(f"File written successfully: '{filepath}'")
        return ExecutionResult(success=True, data={"filepath": filepath, "status": "written"})

    async def _delete_files(self, filepaths: List[str]) -> ExecutionResult:
        """Safely deletes specified files."""
        deleted = []
        for fp in filepaths:
            p = Path(fp)
            if p.exists():
                # Perform backup before deletion
                await self._backup_file(fp)
                p.unlink()
                deleted.append(fp)
        logger.info(f"Deleted {len(deleted)} files safely")
        return ExecutionResult(success=True, data={"deleted_files": deleted, "count": len(deleted)})

    async def _organize_folder(self, target_dir: str) -> ExecutionResult:
        """Organizes a folder by grouping files into extension-based subdirectories."""
        p = Path(target_dir)
        if not p.exists() or not p.is_dir():
            return ExecutionResult(success=False, error_message=f"Directory not found: {target_dir}")

        moves = {}
        for item in p.iterdir():
            if item.is_file():
                ext = item.suffix.lstrip(".").lower() or "misc"
                sub_dir = p / ext.upper()
                sub_dir.mkdir(exist_ok=True)
                dest = sub_dir / item.name
                shutil.move(str(item), str(dest))
                moves[item.name] = str(dest)

        logger.info(f"Organized directory '{target_dir}': moved {len(moves)} files")
        return ExecutionResult(success=True, data={"target_dir": target_dir, "moved_files": moves})

    async def _scan_duplicates(self, target_dir: str) -> ExecutionResult:
        """Scans directory and detects duplicate files using SHA-256 hash comparison."""
        p = Path(target_dir)
        if not p.exists() or not p.is_dir():
            return ExecutionResult(success=False, error_message=f"Directory not found: {target_dir}")

        hashes: Dict[str, List[str]] = {}
        for root, _, files in os.walk(target_dir):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    h = hashlib.sha256(open(filepath, "rb").read()).hexdigest()
                    hashes.setdefault(h, []).append(filepath)
                except Exception:
                    continue

        duplicates = {h: paths for h, paths in hashes.items() if len(paths) > 1}
        logger.info(f"Duplicate scan complete in '{target_dir}': found {len(duplicates)} duplicate sets")
        return ExecutionResult(success=True, data={"duplicates": duplicates, "set_count": len(duplicates)})

    async def _backup_file(self, filepath: str) -> ExecutionResult:
        """Creates a versioned backup copy of a file in .backup directory."""
        p = Path(filepath)
        if not p.exists():
            return ExecutionResult(success=False, error_message=f"File not found: {filepath}")

        backup_dir = p.parent / ".jarvis_backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"{p.stem}_backup_{int(os.path.getmtime(filepath))}{p.suffix}"
        shutil.copy2(str(p), str(backup_path))
        logger.info(f"Versioned backup created: '{backup_path}'")
        return ExecutionResult(success=True, data={"original": filepath, "backup": str(backup_path)})
