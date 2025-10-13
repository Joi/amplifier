"""Backup management for vi editor."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class BackupManager:
    """Manages file backups."""

    def __init__(self, backup_dir: Optional[str] = None):
        """Initialize backup manager.

        Args:
            backup_dir: Directory for backups (default: ~/.vi_backups).
        """
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = Path.home() / ".vi_backups"

        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, filename: str) -> Optional[str]:
        """Create a backup of a file.

        Args:
            filename: Path to the file to backup.

        Returns:
            Path to the backup file or None if failed.
        """
        source = Path(filename)

        if not source.exists():
            return None

        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source.name}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name

        try:
            # Copy file to backup
            shutil.copy2(source, backup_path)
            return str(backup_path)
        except Exception:
            return None

    def get_backups(self, filename: str) -> List[str]:
        """Get list of backups for a file.

        Args:
            filename: Original filename.

        Returns:
            List of backup file paths.
        """
        source = Path(filename)
        pattern = f"{source.name}.*.bak"

        backups = []
        for backup_file in self.backup_dir.glob(pattern):
            backups.append(str(backup_file))

        # Sort by modification time (newest first)
        backups.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)

        return backups

    def restore_backup(self, backup_file: str, target: str) -> bool:
        """Restore a backup file.

        Args:
            backup_file: Path to the backup file.
            target: Path to restore to.

        Returns:
            True if successful, False otherwise.
        """
        backup = Path(backup_file)
        target_path = Path(target)

        if not backup.exists():
            return False

        try:
            # Create backup of current file before restoring
            if target_path.exists():
                self.create_backup(target)

            # Copy backup to target
            shutil.copy2(backup, target_path)
            return True
        except Exception:
            return False

    def delete_backup(self, backup_file: str) -> bool:
        """Delete a backup file.

        Args:
            backup_file: Path to the backup file.

        Returns:
            True if successful, False otherwise.
        """
        backup = Path(backup_file)

        if not backup.exists():
            return False

        try:
            backup.unlink()
            return True
        except Exception:
            return False

    def clean_old_backups(self, days: int = 30) -> int:
        """Clean backups older than specified days.

        Args:
            days: Age threshold in days.

        Returns:
            Number of backups deleted.
        """
        import time

        current_time = time.time()
        threshold = days * 86400  # Convert days to seconds
        deleted = 0

        for backup_file in self.backup_dir.glob("*.bak"):
            age = current_time - backup_file.stat().st_mtime
            if age > threshold:
                try:
                    backup_file.unlink()
                    deleted += 1
                except Exception:
                    pass

        return deleted

    def get_backup_size(self) -> int:
        """Get total size of all backups.

        Returns:
            Total size in bytes.
        """
        total_size = 0
        for backup_file in self.backup_dir.glob("*.bak"):
            total_size += backup_file.stat().st_size
        return total_size
