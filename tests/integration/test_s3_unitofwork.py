"""Integration tests for S3-based Unit of Work classes."""

import io
import zipfile

import pytest

# Check if moto is available
try:
    import boto3
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False

from app.adapters.s3_repository import S3Repository, reset_s3_repository
from app.internal.exceptions import ArtifactNotFoundError


@pytest.fixture(autouse=True)
def reset_s3_singleton():
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


def create_minimal_decomp_zip() -> bytes:
    """Create a minimal DECOMP deck zip for testing."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # caso.dat - defines file extension
        zf.writestr("caso.dat", "rv0\n")
        # Minimal dadger file
        zf.writestr("dadger.rv0", "& dadger test file\n")
        # Minimal hidr.dat
        zf.writestr("hidr.dat", "")
    return buffer.getvalue()


def create_minimal_newave_zip() -> bytes:
    """Create a minimal NEWAVE deck zip for testing."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # caso.dat - defines file extension
        zf.writestr("caso.dat", "arquivos.dat\n")
        # Minimal arquivos.dat
        zf.writestr("arquivos.dat", "dger.dat\n")
        # Minimal dger.dat
        zf.writestr("dger.dat", "& dger test file\n")
    return buffer.getvalue()


def create_minimal_relato() -> bytes:
    """Create a minimal relato file for testing."""
    return b"& relato test file\n"


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestS3DecompUnitOfWork:
    """Integration tests for S3DecompUnitOfWork."""

    @pytest.fixture
    def s3_with_decomp_case(self, aws_credentials):
        """S3 bucket with a DECOMP case uploaded."""
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="decomp-bucket")

            # Upload deck_processado.zip
            deck_zip = create_minimal_decomp_zip()
            client.put_object(
                Bucket="decomp-bucket",
                Key="artifacts/test123/entradas/deck_processado.zip",
                Body=deck_zip,
            )

            yield client

    @pytest.mark.asyncio
    async def test_download_and_extract(
        self, s3_with_decomp_case, tmp_path, monkeypatch
    ):
        """Test that DECOMP case is downloaded and extracted."""
        from app.services.unitofwork import S3DecompUnitOfWork

        # Use tmp_path as temp dir
        monkeypatch.setattr("app.internal.settings.Settings.temp_dir", str(tmp_path))

        s3_repo = S3Repository(region="us-east-1")

        try:
            async with S3DecompUnitOfWork(s3_repo, "decomp-bucket", "test123") as uow:
                # Verify temp dir created
                assert uow.temp_dir is not None
                assert uow.temp_dir.exists()

                # Verify files extracted
                assert (uow.temp_dir / "caso.dat").exists()
                assert (uow.temp_dir / "dadger.rv0").exists()

                # Verify repository available
                assert uow.files is not None
        finally:
            s3_repo.close()

    @pytest.mark.asyncio
    async def test_cleanup_on_exit(self, s3_with_decomp_case, tmp_path, monkeypatch):
        """Test that temp directory is cleaned up on exit."""
        from app.services.unitofwork import S3DecompUnitOfWork

        monkeypatch.setattr("app.internal.settings.Settings.temp_dir", str(tmp_path))

        s3_repo = S3Repository(region="us-east-1")
        temp_dir_path = None

        try:
            async with S3DecompUnitOfWork(s3_repo, "decomp-bucket", "test123") as uow:
                temp_dir_path = uow.temp_dir
                assert temp_dir_path.exists()

            # Should be cleaned up
            assert not temp_dir_path.exists()
        finally:
            s3_repo.close()

    @pytest.mark.asyncio
    async def test_cleanup_on_exception(
        self, s3_with_decomp_case, tmp_path, monkeypatch
    ):
        """Test that temp directory is cleaned up on exception."""
        from app.services.unitofwork import S3DecompUnitOfWork

        monkeypatch.setattr("app.internal.settings.Settings.temp_dir", str(tmp_path))

        s3_repo = S3Repository(region="us-east-1")
        temp_dir_path = None

        try:
            try:
                async with S3DecompUnitOfWork(
                    s3_repo, "decomp-bucket", "test123"
                ) as uow:
                    temp_dir_path = uow.temp_dir
                    raise ValueError("Test error")
            except ValueError:
                pass

            # Should be cleaned up even on exception
            assert not temp_dir_path.exists()
        finally:
            s3_repo.close()

    @pytest.mark.asyncio
    async def test_upload_result(self, s3_with_decomp_case, tmp_path, monkeypatch):
        """Test that results can be uploaded to S3."""
        from app.services.unitofwork import S3DecompUnitOfWork

        monkeypatch.setattr("app.internal.settings.Settings.temp_dir", str(tmp_path))
        monkeypatch.setattr("app.internal.settings.Settings.zip_compression_level", 6)

        s3_repo = S3Repository(region="us-east-1")

        try:
            async with S3DecompUnitOfWork(s3_repo, "decomp-bucket", "test123") as uow:
                # Add a test file
                (uow.temp_dir / "test_output.txt").write_text("test output")

                # Upload result
                output_key = await uow.upload_result()

                assert output_key == "ingest/test123_regras.zip"

                # Verify uploaded to S3
                response = s3_with_decomp_case.get_object(
                    Bucket="decomp-bucket", Key="ingest/test123_regras.zip"
                )
                assert response["Body"].read()
        finally:
            s3_repo.close()

    @pytest.mark.asyncio
    async def test_artifact_not_found(self, aws_credentials, tmp_path, monkeypatch):
        """Test that ArtifactNotFoundError is raised for missing case."""
        from app.services.unitofwork import S3DecompUnitOfWork

        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="decomp-bucket")

            monkeypatch.setattr(
                "app.internal.settings.Settings.temp_dir", str(tmp_path)
            )

            s3_repo = S3Repository(region="us-east-1")

            try:
                with pytest.raises(ArtifactNotFoundError):
                    async with S3DecompUnitOfWork(
                        s3_repo, "decomp-bucket", "nonexistent"
                    ):
                        pass
            finally:
                s3_repo.close()


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestS3NewaveUnitOfWork:
    """Integration tests for S3NewaveUnitOfWork."""

    @pytest.fixture
    def s3_with_newave_case(self, aws_credentials):
        """S3 bucket with a NEWAVE case uploaded."""
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="newave-bucket")

            # Upload deck_processado.zip
            deck_zip = create_minimal_newave_zip()
            client.put_object(
                Bucket="newave-bucket",
                Key="artifacts/newave123/entradas/deck_processado.zip",
                Body=deck_zip,
            )

            yield client

    @pytest.mark.asyncio
    async def test_download_and_extract(
        self, s3_with_newave_case, tmp_path, monkeypatch
    ):
        """Test that NEWAVE case is downloaded and extracted."""
        from app.services.unitofwork import S3NewaveUnitOfWork

        monkeypatch.setattr("app.internal.settings.Settings.temp_dir", str(tmp_path))

        s3_repo = S3Repository(region="us-east-1")

        try:
            async with S3NewaveUnitOfWork(s3_repo, "newave-bucket", "newave123") as uow:
                # Verify temp dir created
                assert uow.temp_dir is not None
                assert uow.temp_dir.exists()

                # Verify files extracted
                assert (uow.temp_dir / "caso.dat").exists()

                # Verify repository available
                assert uow.files is not None
        finally:
            s3_repo.close()

    @pytest.mark.asyncio
    async def test_upload_result(self, s3_with_newave_case, tmp_path, monkeypatch):
        """Test that results can be uploaded to S3."""
        from app.services.unitofwork import S3NewaveUnitOfWork

        monkeypatch.setattr("app.internal.settings.Settings.temp_dir", str(tmp_path))
        monkeypatch.setattr("app.internal.settings.Settings.zip_compression_level", 6)

        s3_repo = S3Repository(region="us-east-1")

        try:
            async with S3NewaveUnitOfWork(s3_repo, "newave-bucket", "newave123") as uow:
                # Upload result
                output_key = await uow.upload_result()

                assert output_key == "ingest/newave123_regras.zip"
        finally:
            s3_repo.close()


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestS3DecompProspectionUnitOfWork:
    """Integration tests for S3DecompProspectionUnitOfWork."""

    @pytest.fixture
    def s3_with_multiple_cases(self, aws_credentials):
        """S3 bucket with multiple DECOMP cases for prospection."""
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="decomp-bucket")

            # Upload first case
            deck_zip1 = create_minimal_decomp_zip()
            client.put_object(
                Bucket="decomp-bucket",
                Key="artifacts/case1/entradas/deck_processado.zip",
                Body=deck_zip1,
            )
            client.put_object(
                Bucket="decomp-bucket",
                Key="artifacts/case1/saidas/relato.rv0",
                Body=create_minimal_relato(),
            )

            # Upload second case
            deck_zip2 = create_minimal_decomp_zip()
            client.put_object(
                Bucket="decomp-bucket",
                Key="artifacts/case2/entradas/deck_processado.zip",
                Body=deck_zip2,
            )
            client.put_object(
                Bucket="decomp-bucket",
                Key="artifacts/case2/saidas/relato.rv0",
                Body=create_minimal_relato(),
            )

            yield client

    @pytest.mark.asyncio
    async def test_download_multiple_sources(
        self, s3_with_multiple_cases, tmp_path, monkeypatch
    ):
        """Test downloading multiple source cases."""
        from app.services.unitofwork import S3DecompProspectionUnitOfWork

        monkeypatch.setattr("app.internal.settings.Settings.temp_dir", str(tmp_path))

        s3_repo = S3Repository(region="us-east-1")
        sources = [
            ("decomp-bucket", "case1"),
            ("decomp-bucket", "case2"),
        ]

        try:
            async with S3DecompProspectionUnitOfWork(s3_repo, sources) as uow:
                # Verify two repositories available
                assert len(uow.repositories) == 2

                # Verify each repository has files
                for repo in uow.repositories:
                    assert repo is not None
        finally:
            s3_repo.close()

    @pytest.mark.asyncio
    async def test_cleanup_all_temp_dirs(
        self, s3_with_multiple_cases, tmp_path, monkeypatch
    ):
        """Test that all temp directories are cleaned up."""
        from app.services.unitofwork import S3DecompProspectionUnitOfWork

        monkeypatch.setattr("app.internal.settings.Settings.temp_dir", str(tmp_path))

        s3_repo = S3Repository(region="us-east-1")
        sources = [
            ("decomp-bucket", "case1"),
            ("decomp-bucket", "case2"),
        ]

        temp_dirs = []

        try:
            async with S3DecompProspectionUnitOfWork(s3_repo, sources):
                # Get list of temp directories created
                temp_dirs = list(tmp_path.glob("decomp_src_*"))
                assert len(temp_dirs) == 2

            # Verify all cleaned up
            remaining = list(tmp_path.glob("decomp_src_*"))
            assert len(remaining) == 0
        finally:
            s3_repo.close()
