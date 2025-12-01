"""
S3 Repository for artifact storage operations.

This module provides async-compatible S3 operations using boto3 wrapped
in a ThreadPoolExecutor to avoid blocking the event loop.
"""

import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.internal.exceptions import ArtifactNotFoundError, S3OperationError
from app.internal.settings import Settings


class AbstractS3Repository(ABC):
    """Abstract interface for S3 operations."""

    @abstractmethod
    async def download_file(
        self, bucket: str, key: str, local_path: str
    ) -> None:
        """
        Download a file from S3 to local filesystem.

        Args:
            bucket: S3 bucket name
            key: S3 object key
            local_path: Local filesystem path to save file

        Raises:
            ArtifactNotFoundError: If object does not exist
            S3OperationError: If download fails
        """
        pass

    @abstractmethod
    async def upload_file(self, local_path: str, bucket: str, key: str) -> str:
        """
        Upload a file from local filesystem to S3.

        Args:
            local_path: Local filesystem path of file
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            The S3 key of the uploaded object

        Raises:
            S3OperationError: If upload fails
        """
        pass

    @abstractmethod
    async def download_bytes(self, bucket: str, key: str) -> bytes:
        """
        Download object content as bytes.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            Object content as bytes

        Raises:
            ArtifactNotFoundError: If object does not exist
            S3OperationError: If download fails
        """
        pass

    @abstractmethod
    async def object_exists(self, bucket: str, key: str) -> bool:
        """
        Check if an object exists in S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if object exists, False otherwise
        """
        pass

    @abstractmethod
    async def list_objects(
        self, bucket: str, prefix: str, max_keys: int = 1000
    ) -> list[str]:
        """
        List objects with a given prefix.

        Args:
            bucket: S3 bucket name
            prefix: Key prefix to filter by
            max_keys: Maximum number of keys to return

        Returns:
            List of object keys matching prefix
        """
        pass


class S3Repository(AbstractS3Repository):
    """
    S3 repository implementation using boto3 with async wrapper.

    Uses ThreadPoolExecutor to run synchronous boto3 calls without
    blocking the async event loop.

    Example:
        >>> repo = S3Repository(region="us-east-1")
        >>> await repo.download_file("bucket", "key", "/tmp/file.txt")
    """

    def __init__(
        self,
        region: str,
        endpoint_url: str | None = None,
        max_workers: int = 4,
    ):
        """
        Initialize S3 repository.

        Args:
            region: AWS region name
            endpoint_url: Optional custom endpoint (for MinIO/LocalStack)
            max_workers: Thread pool size for async operations
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
            max_pool_connections=max_workers,
        )

        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            config=config,
        )

    async def download_file(
        self, bucket: str, key: str, local_path: str
    ) -> None:
        """Download a file from S3 to local filesystem."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                self._executor,
                self._client.download_file,
                bucket,
                key,
                local_path,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404" or error_code == "NoSuchKey":
                raise ArtifactNotFoundError(
                    f"Object not found: s3://{bucket}/{key}",
                    details={"bucket": bucket, "key": key},
                )
            raise S3OperationError(
                f"Failed to download s3://{bucket}/{key}: {e}",
                details={"bucket": bucket, "key": key, "error": str(e)},
            )

    async def upload_file(self, local_path: str, bucket: str, key: str) -> str:
        """Upload a file from local filesystem to S3."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                self._executor,
                self._client.upload_file,
                local_path,
                bucket,
                key,
            )
            return key
        except ClientError as e:
            raise S3OperationError(
                f"Failed to upload to s3://{bucket}/{key}: {e}",
                details={"bucket": bucket, "key": key, "error": str(e)},
            )

    async def download_bytes(self, bucket: str, key: str) -> bytes:
        """Download object content as bytes."""
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                self._executor,
                lambda: self._client.get_object(Bucket=bucket, Key=key),
            )
            body: bytes = response["Body"].read()
            return body
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404" or error_code == "NoSuchKey":
                raise ArtifactNotFoundError(
                    f"Object not found: s3://{bucket}/{key}",
                    details={"bucket": bucket, "key": key},
                )
            raise S3OperationError(
                f"Failed to download s3://{bucket}/{key}: {e}",
                details={"bucket": bucket, "key": key, "error": str(e)},
            )

    async def object_exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in S3."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                self._executor,
                lambda: self._client.head_object(Bucket=bucket, Key=key),
            )
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                return False
            raise S3OperationError(
                f"Failed to check existence of s3://{bucket}/{key}: {e}",
                details={"bucket": bucket, "key": key, "error": str(e)},
            )

    async def list_objects(
        self, bucket: str, prefix: str, max_keys: int = 1000
    ) -> list[str]:
        """List objects with a given prefix."""
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                self._executor,
                lambda: self._client.list_objects_v2(
                    Bucket=bucket,
                    Prefix=prefix,
                    MaxKeys=max_keys,
                ),
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
        except ClientError as e:
            raise S3OperationError(
                f"Failed to list objects in s3://{bucket}/{prefix}: {e}",
                details={"bucket": bucket, "prefix": prefix, "error": str(e)},
            )

    def close(self) -> None:
        """Shutdown the thread pool executor."""
        self._executor.shutdown(wait=True)


# =============================================================================
# Factory Functions
# =============================================================================

# Module-level singleton
_s3_repository: S3Repository | None = None


def get_s3_repository() -> S3Repository:
    """
    Get or create the S3Repository singleton.

    Uses Settings for configuration. The repository is created once
    and reused for all requests (connection pooling).

    Returns:
        S3Repository instance

    Example:
        from app.adapters.s3_repository import get_s3_repository

        s3_repo = get_s3_repository()
        await s3_repo.download_file(bucket, key, path)
    """
    global _s3_repository

    if _s3_repository is None:
        _s3_repository = S3Repository(
            region=Settings.aws_region,
            endpoint_url=Settings.s3_endpoint_url,
        )

    return _s3_repository


def reset_s3_repository() -> None:
    """
    Reset the S3Repository singleton.

    Useful for testing to ensure clean state between tests.
    Closes the existing repository's thread pool before resetting.
    """
    global _s3_repository

    if _s3_repository is not None:
        _s3_repository.close()
        _s3_repository = None


def set_s3_repository(repo: S3Repository) -> None:
    """
    Set a custom S3Repository instance.

    Useful for testing with mock repositories.

    Args:
        repo: S3Repository instance to use
    """
    global _s3_repository
    _s3_repository = repo
