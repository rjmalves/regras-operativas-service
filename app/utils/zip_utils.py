"""
Zip file utilities for artifact handling.

This module provides functions to extract and create zip files
for NEWAVE/DECOMP deck processing.
"""

import zipfile
from pathlib import Path

from app.internal.exceptions import ZipExtractionError
from app.utils.log import Log


def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """
    Extract a zip file to a destination directory.

    All files are extracted to the root of dest_dir (no subdirectories).

    Args:
        zip_path: Path to the zip file
        dest_dir: Directory to extract files to

    Raises:
        ZipExtractionError: If extraction fails
    """
    Log.log().info(f"Extracting {zip_path} to {dest_dir}")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Validate zip integrity
            bad_file = zf.testzip()
            if bad_file is not None:
                raise ZipExtractionError(
                    f"Corrupted file in archive: {bad_file}",
                    details={"zip_path": str(zip_path), "bad_file": bad_file},
                )

            zf.extractall(dest_dir)
    except zipfile.BadZipFile as e:
        raise ZipExtractionError(
            f"Invalid zip file: {zip_path}",
            details={"zip_path": str(zip_path), "error": str(e)},
        )
    except FileNotFoundError:
        raise ZipExtractionError(
            f"Zip file not found: {zip_path}",
            details={"zip_path": str(zip_path)},
        )

    Log.log().info(f"Extracted {len(list(dest_dir.iterdir()))} files")


def create_zip(
    source_dir: Path,
    zip_path: Path,
    compression_level: int = 6,
) -> None:
    """
    Create a zip file from all files in a directory.

    Files are added at root level (no directory structure preserved).

    Args:
        source_dir: Directory containing files to zip
        zip_path: Path for the output zip file
        compression_level: Compression level (0-9, default 6)

    Raises:
        ZipExtractionError: If creation fails
    """
    if not source_dir.exists():
        raise ZipExtractionError(
            f"Source directory not found: {source_dir}",
            details={"source_dir": str(source_dir)},
        )

    files = [f for f in source_dir.iterdir() if f.is_file()]
    if not files:
        raise ZipExtractionError(
            f"Source directory is empty: {source_dir}",
            details={"source_dir": str(source_dir)},
        )

    Log.log().info(f"Creating zip {zip_path} from {len(files)} files")

    try:
        with zipfile.ZipFile(
            zip_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=compression_level,
        ) as zf:
            for file_path in files:
                # Add file at root level (just filename, no path)
                zf.write(file_path, file_path.name)
    except Exception as e:
        raise ZipExtractionError(
            f"Failed to create zip: {zip_path}",
            details={"zip_path": str(zip_path), "error": str(e)},
        )

    Log.log().info(f"Created zip: {zip_path} ({zip_path.stat().st_size} bytes)")


def get_zip_file_list(zip_path: Path) -> list[str]:
    """
    Get list of files in a zip archive.

    Args:
        zip_path: Path to the zip file

    Returns:
        List of filenames in the archive

    Raises:
        ZipExtractionError: If zip cannot be read
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            return zf.namelist()
    except zipfile.BadZipFile as e:
        raise ZipExtractionError(
            f"Invalid zip file: {zip_path}",
            details={"zip_path": str(zip_path), "error": str(e)},
        )
    except FileNotFoundError:
        raise ZipExtractionError(
            f"Zip file not found: {zip_path}",
            details={"zip_path": str(zip_path)},
        )
