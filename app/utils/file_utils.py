import zipfile
from typing import List
from pathlib import Path

import config

# Only allow source code and build files inside submissions
ALLOWED_EXTENSIONS = {
    ".c", ".h", ".cpp", ".cc", ".hpp", ".cxx",
    ".txt", ".md", ".json",
    ".sh", ".py",
    "",  # Makefile has no extension
}

# Max compression ratio to detect zip bombs (uncompressed / compressed)
MAX_COMPRESSION_RATIO = 100


def safe_extract_zip(zip_path: Path, dest_dir: Path, max_total_bytes: int = None) -> List[str]:
    """Extract a ZIP file safely, returning list of extracted file names.

    Raises ValueError on path traversal, size violations, disallowed files, or zip bombs.
    """
    if max_total_bytes is None:
        max_total_bytes = config.MAX_SUBMISSION_SIZE_MB * 1024 * 1024

    # Zip bomb check: compare compressed vs declared uncompressed size
    compressed_size = zip_path.stat().st_size
    if compressed_size == 0:
        raise ValueError("Arquivo ZIP vazio")

    extracted = []
    total_size = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Check total declared size before extracting anything
        declared_total = sum(i.file_size for i in zf.infolist() if not i.is_dir())
        if declared_total > max_total_bytes:
            raise ValueError(
                f"Tamanho total descompactado ({declared_total // 1024}KB) "
                f"excede o limite de {max_total_bytes // (1024*1024)}MB"
            )
        if compressed_size > 0 and declared_total / compressed_size > MAX_COMPRESSION_RATIO:
            raise ValueError(
                f"Razão de compressão suspeita ({declared_total / compressed_size:.0f}x). "
                f"Arquivo rejeitado."
            )

        # Check max file count
        file_count = sum(1 for i in zf.infolist() if not i.is_dir())
        if file_count > 200:
            raise ValueError(f"ZIP contém {file_count} arquivos (máximo: 200)")

        for info in zf.infolist():
            if info.is_dir():
                continue

            # Path traversal prevention
            target = (dest_dir / info.filename).resolve()
            if not str(target).startswith(str(dest_dir.resolve())):
                raise ValueError(f"Path traversal detectado: {info.filename}")

            # Extension whitelist
            ext = Path(info.filename).suffix.lower()
            name = Path(info.filename).name
            if ext not in ALLOWED_EXTENSIONS and name != "Makefile":
                raise ValueError(
                    f"Tipo de arquivo não permitido: {info.filename} "
                    f"(extensões aceitas: {', '.join(sorted(e for e in ALLOWED_EXTENSIONS if e))})"
                )

            # Individual file size
            if info.file_size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
                raise ValueError(
                    f"Arquivo muito grande: {info.filename} "
                    f"({info.file_size // 1024}KB, máximo: {config.MAX_FILE_SIZE_MB}MB)"
                )

            total_size += info.file_size
            if total_size > max_total_bytes:
                raise ValueError(
                    f"Tamanho total extraído excede {max_total_bytes // (1024*1024)}MB"
                )

            # Extract
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            extracted.append(info.filename)

    return extracted


def sanitize_filename(name: str) -> str:
    """Remove unsafe characters from a filename."""
    safe = "".join(c for c in name if c.isalnum() or c in ".-_")
    return safe or "unnamed"
