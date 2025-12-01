"""Unit tests for S3Repository."""

import pytest

from app.adapters.s3_repository import (
    S3Repository,
    get_s3_repository,
    reset_s3_repository,
    set_s3_repository,
)
from app.internal.exceptions import ArtifactNotFoundError, S3OperationError

# Check if moto is available
try:
    import boto3
    from moto import mock_aws
    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset S3Repository singleton before each test."""
    reset_s3_repository()
    yield
    reset_s3_repository()


@pytest.fixture
def aws_credentials(monkeypatch):
    """Set fake AWS credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestS3Repository:
    """Tests for S3Repository with moto."""

    @pytest.fixture
    def s3_setup(self, aws_credentials):
        """Set up mocked S3 environment."""
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="test-bucket")
            yield client

    @pytest.fixture
    def s3_repo(self, s3_setup):
        """Create S3Repository for testing."""
        repo = S3Repository(region="us-east-1")
        yield repo
        repo.close()

    @pytest.mark.asyncio
    async def test_download_file_success(self, s3_repo, s3_setup, tmp_path):
        """Test downloading a file."""
        # Upload test file
        s3_setup.put_object(
            Bucket="test-bucket",
            Key="test/file.txt",
            Body=b"test content",
        )

        # Download
        local_path = tmp_path / "downloaded.txt"
        await s3_repo.download_file("test-bucket", "test/file.txt", str(local_path))

        assert local_path.read_bytes() == b"test content"

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, s3_repo, s3_setup, tmp_path):
        """Test downloading non-existent file."""
        local_path = tmp_path / "downloaded.txt"

        with pytest.raises(ArtifactNotFoundError) as exc_info:
            await s3_repo.download_file("test-bucket", "nonexistent.txt", str(local_path))

        assert "test-bucket" in exc_info.value.details.get("bucket", "")

    @pytest.mark.asyncio
    async def test_upload_file_success(self, s3_repo, s3_setup, tmp_path):
        """Test uploading a file."""
        local_file = tmp_path / "upload.txt"
        local_file.write_bytes(b"upload content")

        key = await s3_repo.upload_file(str(local_file), "test-bucket", "uploaded.txt")

        assert key == "uploaded.txt"
        response = s3_setup.get_object(Bucket="test-bucket", Key="uploaded.txt")
        assert response["Body"].read() == b"upload content"

    @pytest.mark.asyncio
    async def test_download_bytes_success(self, s3_repo, s3_setup):
        """Test downloading object as bytes."""
        s3_setup.put_object(
            Bucket="test-bucket",
            Key="bytes/file.bin",
            Body=b"\x00\x01\x02\x03",
        )

        content = await s3_repo.download_bytes("test-bucket", "bytes/file.bin")

        assert content == b"\x00\x01\x02\x03"

    @pytest.mark.asyncio
    async def test_download_bytes_not_found(self, s3_repo, s3_setup):
        """Test downloading non-existent object as bytes."""
        with pytest.raises(ArtifactNotFoundError):
            await s3_repo.download_bytes("test-bucket", "nonexistent.bin")

    @pytest.mark.asyncio
    async def test_object_exists_true(self, s3_repo, s3_setup):
        """Test object_exists returns True for existing object."""
        s3_setup.put_object(
            Bucket="test-bucket",
            Key="exists.txt",
            Body=b"content",
        )

        exists = await s3_repo.object_exists("test-bucket", "exists.txt")

        assert exists is True

    @pytest.mark.asyncio
    async def test_object_exists_false(self, s3_repo, s3_setup):
        """Test object_exists returns False for missing object."""
        exists = await s3_repo.object_exists("test-bucket", "nonexistent.txt")

        assert exists is False

    @pytest.mark.asyncio
    async def test_list_objects(self, s3_repo, s3_setup):
        """Test listing objects with prefix."""
        s3_setup.put_object(Bucket="test-bucket", Key="prefix/file1.txt", Body=b"1")
        s3_setup.put_object(Bucket="test-bucket", Key="prefix/file2.txt", Body=b"2")
        s3_setup.put_object(Bucket="test-bucket", Key="other/file3.txt", Body=b"3")

        keys = await s3_repo.list_objects("test-bucket", "prefix/")

        assert set(keys) == {"prefix/file1.txt", "prefix/file2.txt"}

    @pytest.mark.asyncio
    async def test_list_objects_empty(self, s3_repo, s3_setup):
        """Test listing objects with no matches."""
        keys = await s3_repo.list_objects("test-bucket", "nonexistent/")

        assert keys == []


class TestS3RepositorySingleton:
    """Tests for S3Repository singleton functions."""

    def test_reset_clears_singleton(self, monkeypatch):
        """Test reset_s3_repository clears the singleton."""
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        # Note: We can't actually test get_s3_repository without moto
        # but we can test reset doesn't crash
        reset_s3_repository()

    def test_set_s3_repository(self):
        """Test set_s3_repository sets custom instance."""
        # Create a mock repo (not a real one to avoid AWS calls)
        class MockRepo:
            def close(self):
                pass

        mock_repo = MockRepo()
        set_s3_repository(mock_repo)

        # Clean up
        reset_s3_repository()


class TestS3RepositoryInit:
    """Tests for S3Repository initialization."""

    @pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
    def test_init_with_endpoint_url(self, aws_credentials):
        """Test initialization with custom endpoint."""
        with mock_aws():
            repo = S3Repository(
                region="us-east-1",
                endpoint_url="http://localhost:4566",
            )
            assert repo is not None
            repo.close()

    @pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
    def test_init_with_custom_workers(self, aws_credentials):
        """Test initialization with custom worker count."""
        with mock_aws():
            repo = S3Repository(
                region="us-east-1",
                max_workers=8,
            )
            assert repo is not None
            repo.close()
