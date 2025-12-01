from abc import ABC, abstractmethod
from os import chdir, curdir
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import tempfile

from app.models.program import Program
from app.adapters.newaverepository import (
    AbstractNewaveRepository,
    RawNewaveRepository,
)
from app.adapters.decomprepository import (
    AbstractDecompRepository,
    RawDecompRepository,
)
from app.internal.settings import Settings
from app.utils.log import Log
from app.utils.zip_utils import extract_zip, create_zip
from app.utils.temp_manager import cleanup_directory


class AbstractUnitOfWork(ABC):
    def __enter__(self) -> "AbstractUnitOfWork":
        return self

    def __exit__(self, *args):
        self.rollback()

    @abstractmethod
    def rollback(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def program(self) -> Program:
        raise NotImplementedError

    @property
    @abstractmethod
    def files(
        self,
    ) -> Union[AbstractNewaveRepository, AbstractDecompRepository]:
        raise NotImplementedError


class NewaveUnitOfWork(AbstractUnitOfWork):
    def __init__(self, directory: str):
        self._current_path = Path(curdir).resolve()
        self._case_directory = directory
        self._newave = None

    def __create_repository(self):
        if self._newave is None:
            self._newave = RawNewaveRepository(str(self._case_directory))

    def __enter__(self) -> "NewaveUnitOfWork":
        chdir(self._case_directory)
        self.__create_repository()
        return super().__enter__()

    def __exit__(self, *args):
        chdir(self._current_path)
        super().__exit__(*args)

    @property
    def program(self) -> Program:
        return Program.NEWAVE

    @property
    def files(self) -> AbstractNewaveRepository:
        return self._newave

    def rollback(self):
        pass


class DecompUnitOfWork(AbstractUnitOfWork):
    def __init__(self, directory: str):
        self._current_path = Path(curdir).resolve()
        self._case_directory = directory
        self._decomp = None

    def __create_repository(self):
        if self._decomp is None:
            self._decomp = RawDecompRepository(str(self._case_directory))

    def __enter__(self) -> "DecompUnitOfWork":
        chdir(self._case_directory)
        self.__create_repository()
        return super().__enter__()

    def __exit__(self, *args):
        chdir(self._current_path)
        super().__exit__(*args)

    @property
    def program(self) -> Program:
        return Program.DECOMP

    @property
    def files(self) -> AbstractDecompRepository:
        return self._decomp

    def rollback(self):
        pass


def factory(kind: Program, *args, **kwargs) -> AbstractUnitOfWork:
    mappings: Dict[Program, AbstractUnitOfWork] = {
        Program.NEWAVE: NewaveUnitOfWork,
        Program.DECOMP: DecompUnitOfWork,
    }
    return mappings[kind](*args, **kwargs)


# =============================================================================
# S3-based Unit of Work Classes
# =============================================================================


class S3DecompUnitOfWork:
    """
    Unit of Work for a single DECOMP case from S3.
    
    Downloads deck_processado.zip, extracts to temp dir, provides file access,
    and supports uploading modified results back to S3.
    
    Example:
        async with S3DecompUnitOfWork(s3_repo, "bucket", "hash123") as uow:
            files = uow.files
            # modify files
            output_key = await uow.upload_result()
    """
    
    def __init__(
        self,
        s3_repo,  # S3Repository - avoid circular import
        bucket: str,
        execution_hash: str,
        output_prefix: str = "ingest",
    ):
        self._s3_repo = s3_repo
        self._bucket = bucket
        self._execution_hash = execution_hash
        self._output_prefix = output_prefix
        self._temp_dir: Optional[Path] = None
        self._decomp: Optional[RawDecompRepository] = None
    
    async def __aenter__(self) -> "S3DecompUnitOfWork":
        """Download and extract DECOMP case from S3."""
        # Create temp directory
        base_dir = Path(Settings.temp_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dir = Path(tempfile.mkdtemp(
            dir=str(base_dir),
            prefix="decomp_"
        ))
        Log.log().info(f"Created temp directory: {self._temp_dir}")
        
        # Download and extract deck
        zip_key = f"artifacts/{self._execution_hash}/entradas/deck_processado.zip"
        zip_path = self._temp_dir / "deck_processado.zip"
        
        Log.log().info(f"Downloading s3://{self._bucket}/{zip_key}")
        await self._s3_repo.download_file(self._bucket, zip_key, str(zip_path))
        
        extract_zip(zip_path, self._temp_dir)
        zip_path.unlink()  # Remove zip after extraction
        
        # Create repository
        self._decomp = RawDecompRepository(str(self._temp_dir))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up temp directory."""
        if self._temp_dir:
            cleanup_directory(self._temp_dir)
    
    @property
    def program(self) -> Program:
        return Program.DECOMP
    
    @property
    def files(self) -> AbstractDecompRepository:
        """Access to DECOMP files via repository."""
        return self._decomp
    
    @property
    def temp_dir(self) -> Optional[Path]:
        """Access to temp directory path."""
        return self._temp_dir
    
    async def upload_result(self) -> str:
        """
        Zip temp directory and upload to S3.
        
        Returns:
            S3 key of uploaded file
        """
        output_key = f"{self._output_prefix}/{self._execution_hash}_regras.zip"
        zip_path = self._temp_dir.parent / f"{self._execution_hash}_regras.zip"
        
        Log.log().info(f"Creating zip at {zip_path}")
        create_zip(self._temp_dir, zip_path, Settings.zip_compression_level)
        
        Log.log().info(f"Uploading to s3://{self._bucket}/{output_key}")
        await self._s3_repo.upload_file(str(zip_path), self._bucket, output_key)
        zip_path.unlink()
        
        return output_key


class S3DecompProspectionUnitOfWork:
    """
    Unit of Work for multiple DECOMP source cases (prospection).
    
    Downloads multiple cases for reading reservoir storage data from relato files.
    This is read-only - does NOT upload results.
    
    Example:
        sources = [("bucket1", "hash1"), ("bucket2", "hash2")]
        async with S3DecompProspectionUnitOfWork(s3_repo, sources) as uow:
            for repo in uow.repositories:
                relato = repo.get_relato()
                # read storage data
    """
    
    def __init__(
        self,
        s3_repo,  # S3Repository
        sources: List[Tuple[str, str]],  # List of (bucket, execution_hash)
    ):
        self._s3_repo = s3_repo
        self._sources = sources
        self._temp_dirs: List[Path] = []
        self._repositories: List[RawDecompRepository] = []
    
    async def __aenter__(self) -> "S3DecompProspectionUnitOfWork":
        """Download and extract all source cases."""
        base_dir = Path(Settings.temp_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        
        for bucket, execution_hash in self._sources:
            temp_dir = Path(tempfile.mkdtemp(
                dir=str(base_dir),
                prefix=f"decomp_src_{execution_hash[:8]}_"
            ))
            self._temp_dirs.append(temp_dir)
            Log.log().info(f"Created temp directory: {temp_dir}")
            
            # Download deck and relato
            await self._download_source_files(bucket, execution_hash, temp_dir)
            
            # Create repository
            repo = RawDecompRepository(str(temp_dir))
            self._repositories.append(repo)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up all temp directories."""
        for temp_dir in self._temp_dirs:
            cleanup_directory(temp_dir)
    
    async def _download_source_files(
        self, bucket: str, execution_hash: str, temp_dir: Path
    ) -> None:
        """Download deck zip and relato file for a source case."""
        from idecomp.decomp.caso import Caso
        
        # Download and extract deck
        zip_key = f"artifacts/{execution_hash}/entradas/deck_processado.zip"
        zip_path = temp_dir / "deck_processado.zip"
        
        Log.log().info(f"Downloading s3://{bucket}/{zip_key}")
        await self._s3_repo.download_file(bucket, zip_key, str(zip_path))
        
        extract_zip(zip_path, temp_dir)
        zip_path.unlink()
        
        # Read caso.dat to get extension for relato file
        caso = Caso.read(str(temp_dir / "caso.dat"))
        
        # Download relato
        relato_key = f"artifacts/{execution_hash}/saidas/relato.{caso.arquivos}"
        relato_path = temp_dir / f"relato.{caso.arquivos}"
        
        Log.log().info(f"Downloading s3://{bucket}/{relato_key}")
        await self._s3_repo.download_file(bucket, relato_key, str(relato_path))
    
    @property
    def repositories(self) -> List[RawDecompRepository]:
        """Access to all source repositories for prospection."""
        return self._repositories


class S3NewaveUnitOfWork:
    """
    Unit of Work for a single NEWAVE case from S3.
    
    Downloads deck_processado.zip, extracts to temp dir, provides file access,
    and supports uploading modified results back to S3.
    
    Example:
        async with S3NewaveUnitOfWork(s3_repo, "bucket", "hash123") as uow:
            files = uow.files
            # modify files
            output_key = await uow.upload_result()
    """
    
    def __init__(
        self,
        s3_repo,  # S3Repository
        bucket: str,
        execution_hash: str,
        output_prefix: str = "ingest",
    ):
        self._s3_repo = s3_repo
        self._bucket = bucket
        self._execution_hash = execution_hash
        self._output_prefix = output_prefix
        self._temp_dir: Optional[Path] = None
        self._newave: Optional[RawNewaveRepository] = None
    
    async def __aenter__(self) -> "S3NewaveUnitOfWork":
        """Download and extract NEWAVE case from S3."""
        # Create temp directory
        base_dir = Path(Settings.temp_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dir = Path(tempfile.mkdtemp(
            dir=str(base_dir),
            prefix="newave_"
        ))
        Log.log().info(f"Created temp directory: {self._temp_dir}")
        
        # Download and extract deck
        zip_key = f"artifacts/{self._execution_hash}/entradas/deck_processado.zip"
        zip_path = self._temp_dir / "deck_processado.zip"
        
        Log.log().info(f"Downloading s3://{self._bucket}/{zip_key}")
        await self._s3_repo.download_file(self._bucket, zip_key, str(zip_path))
        
        extract_zip(zip_path, self._temp_dir)
        zip_path.unlink()  # Remove zip after extraction
        
        # Create repository
        self._newave = RawNewaveRepository(str(self._temp_dir))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up temp directory."""
        if self._temp_dir:
            cleanup_directory(self._temp_dir)
    
    @property
    def program(self) -> Program:
        return Program.NEWAVE
    
    @property
    def files(self) -> AbstractNewaveRepository:
        """Access to NEWAVE files via repository."""
        return self._newave
    
    @property
    def temp_dir(self) -> Optional[Path]:
        """Access to temp directory path."""
        return self._temp_dir
    
    async def upload_result(self) -> str:
        """
        Zip temp directory and upload to S3.
        
        Returns:
            S3 key of uploaded file
        """
        output_key = f"{self._output_prefix}/{self._execution_hash}_regras.zip"
        zip_path = self._temp_dir.parent / f"{self._execution_hash}_regras.zip"
        
        Log.log().info(f"Creating zip at {zip_path}")
        create_zip(self._temp_dir, zip_path, Settings.zip_compression_level)
        
        Log.log().info(f"Uploading to s3://{self._bucket}/{output_key}")
        await self._s3_repo.upload_file(str(zip_path), self._bucket, output_key)
        zip_path.unlink()
        
        return output_key


# =============================================================================
# Sync-Compatible Wrapper Classes for S3 Unit of Work
# =============================================================================
# These wrappers provide synchronous context manager compatibility
# with the existing business logic in reservoirrulerepository.py


class S3DecompUnitOfWorkSync(AbstractUnitOfWork):
    """
    Synchronous wrapper for S3DecompUnitOfWork.
    
    This class wraps an already-initialized S3DecompUnitOfWork and provides
    a synchronous context manager compatible with existing business logic.
    
    The async download/upload operations should be done by the caller using
    the underlying S3DecompUnitOfWork; this wrapper provides sync access to
    the files once downloaded.
    """
    
    def __init__(self, s3_uow: S3DecompUnitOfWork):
        self._s3_uow = s3_uow
        self._current_path = Path(curdir).resolve()
    
    def __enter__(self) -> "S3DecompUnitOfWorkSync":
        if self._s3_uow.temp_dir:
            chdir(self._s3_uow.temp_dir)
        return self
    
    def __exit__(self, *args):
        chdir(self._current_path)
        self.rollback()
    
    @property
    def program(self) -> Program:
        return Program.DECOMP
    
    @property
    def files(self) -> AbstractDecompRepository:
        return self._s3_uow.files
    
    def rollback(self):
        pass


class S3NewaveUnitOfWorkSync(AbstractUnitOfWork):
    """
    Synchronous wrapper for S3NewaveUnitOfWork.
    
    This class wraps an already-initialized S3NewaveUnitOfWork and provides
    a synchronous context manager compatible with existing business logic.
    """
    
    def __init__(self, s3_uow: S3NewaveUnitOfWork):
        self._s3_uow = s3_uow
        self._current_path = Path(curdir).resolve()
    
    def __enter__(self) -> "S3NewaveUnitOfWorkSync":
        if self._s3_uow.temp_dir:
            chdir(self._s3_uow.temp_dir)
        return self
    
    def __exit__(self, *args):
        chdir(self._current_path)
        self.rollback()
    
    @property
    def program(self) -> Program:
        return Program.NEWAVE
    
    @property
    def files(self) -> AbstractNewaveRepository:
        return self._s3_uow.files
    
    def rollback(self):
        pass


class S3DecompProspectionSync(AbstractUnitOfWork):
    """
    Synchronous wrapper for individual repository from S3DecompProspectionUnitOfWork.
    
    Wraps a single RawDecompRepository that was downloaded by the async
    prospection unit of work, providing synchronous access compatible
    with existing business logic.
    """
    
    def __init__(self, repository: RawDecompRepository, temp_dir: Path):
        self._repository = repository
        self._temp_dir = temp_dir
        self._current_path = Path(curdir).resolve()
    
    def __enter__(self) -> "S3DecompProspectionSync":
        if self._temp_dir:
            chdir(self._temp_dir)
        return self
    
    def __exit__(self, *args):
        chdir(self._current_path)
        self.rollback()
    
    @property
    def program(self) -> Program:
        return Program.DECOMP
    
    @property
    def files(self) -> AbstractDecompRepository:
        return self._repository
    
    def rollback(self):
        pass
