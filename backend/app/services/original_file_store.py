from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from app.core.config import settings


class OriginalFileStore:
    def __init__(self, root_dir: str | Path | None = None) -> None:
        configured_root = root_dir or settings.original_file_store_dir
        if configured_root is None:
            configured_root = Path.cwd() / "data" / "originals"
        self._root_dir = Path(configured_root)

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    def store_source_file(
        self,
        *,
        workspace_id: str,
        document_id: str,
        content_hash: str,
        filename: str,
        source_bytes: bytes,
    ) -> dict[str, object]:
        safe_name = Path(filename).name or "upload.bin"
        relative_path = Path(workspace_id) / document_id / content_hash / safe_name
        target_path = self._root_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(source_bytes)
        return {
            "relative_path": relative_path.as_posix(),
            "filename": safe_name,
            "content_hash": content_hash,
            "byte_size": len(source_bytes),
            "sha256": sha256(source_bytes).hexdigest(),
        }

    def resolve_relative_path(self, relative_path: str) -> Path:
        return self._root_dir / Path(relative_path)