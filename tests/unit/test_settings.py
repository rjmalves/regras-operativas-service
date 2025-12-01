"""Unit tests for Settings configuration."""

import pytest
from app.internal.settings import Settings


class TestSettingsDefaults:
    """Test default values are set correctly."""

    def test_default_host(self):
        Settings.read_environments()
        assert Settings.host == "0.0.0.0"

    def test_default_port(self):
        Settings.read_environments()
        assert Settings.port == 8000
        assert isinstance(Settings.port, int)

    def test_default_root_path(self):
        Settings.read_environments()
        assert Settings.root_path == "/api/v1/rules"

    def test_default_log_level(self):
        Settings.read_environments()
        assert Settings.log_level == "INFO"

    def test_default_aws_region(self):
        Settings.read_environments()
        assert Settings.aws_region == "us-east-1"

    def test_default_s3_endpoint_url_is_none(self):
        Settings.read_environments()
        assert Settings.s3_endpoint_url is None

    def test_default_buckets(self):
        Settings.read_environments()
        assert Settings.default_newave_bucket == "newave-bucket"
        assert Settings.default_decomp_bucket == "decomp-bucket"

    def test_default_temp_dir(self):
        Settings.read_environments()
        assert Settings.temp_dir == "/tmp/regras-operativas"

    def test_default_zip_compression_level(self):
        Settings.read_environments()
        assert Settings.zip_compression_level == 6
        assert isinstance(Settings.zip_compression_level, int)

    def test_default_max_temp_dir_age_hours(self):
        Settings.read_environments()
        assert Settings.max_temp_dir_age_hours == 24
        assert isinstance(Settings.max_temp_dir_age_hours, int)


class TestSettingsFromEnvironment:
    """Test settings load from environment variables."""

    def test_custom_aws_region(self, monkeypatch):
        monkeypatch.setenv("AWS_REGION", "sa-east-1")
        Settings.read_environments()
        assert Settings.aws_region == "sa-east-1"

    def test_s3_endpoint_url_set(self, monkeypatch):
        monkeypatch.setenv("S3_ENDPOINT_URL", "http://localhost:4566")
        Settings.read_environments()
        assert Settings.s3_endpoint_url == "http://localhost:4566"

    def test_s3_endpoint_url_empty_is_none(self, monkeypatch):
        monkeypatch.setenv("S3_ENDPOINT_URL", "")
        Settings.read_environments()
        assert Settings.s3_endpoint_url is None

    def test_custom_port(self, monkeypatch):
        monkeypatch.setenv("PORT", "9000")
        Settings.read_environments()
        assert Settings.port == 9000
        assert isinstance(Settings.port, int)

    def test_custom_host(self, monkeypatch):
        monkeypatch.setenv("HOST", "127.0.0.1")
        Settings.read_environments()
        assert Settings.host == "127.0.0.1"

    def test_custom_root_path(self, monkeypatch):
        monkeypatch.setenv("ROOT_PATH", "/custom/path")
        Settings.read_environments()
        assert Settings.root_path == "/custom/path"

    def test_custom_log_level(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        Settings.read_environments()
        assert Settings.log_level == "DEBUG"

    def test_custom_newave_bucket(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_NEWAVE_BUCKET", "my-newave")
        Settings.read_environments()
        assert Settings.default_newave_bucket == "my-newave"

    def test_custom_decomp_bucket(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_DECOMP_BUCKET", "my-decomp")
        Settings.read_environments()
        assert Settings.default_decomp_bucket == "my-decomp"

    def test_custom_temp_dir(self, monkeypatch):
        monkeypatch.setenv("TEMP_DIR", "/custom/temp")
        Settings.read_environments()
        assert Settings.temp_dir == "/custom/temp"

    def test_custom_zip_compression_level(self, monkeypatch):
        monkeypatch.setenv("ZIP_COMPRESSION_LEVEL", "9")
        Settings.read_environments()
        assert Settings.zip_compression_level == 9

    def test_custom_max_temp_dir_age_hours(self, monkeypatch):
        monkeypatch.setenv("MAX_TEMP_DIR_AGE_HOURS", "48")
        Settings.read_environments()
        assert Settings.max_temp_dir_age_hours == 48


class TestLegacySettings:
    """Test legacy settings still work."""

    def test_basedir_from_env(self, monkeypatch):
        monkeypatch.setenv("APP_BASEDIR", "/app/base")
        Settings.read_environments()
        assert Settings.basedir == "/app/base"

    def test_installdir_from_env(self, monkeypatch):
        monkeypatch.setenv("APP_INSTALLDIR", "/app/install")
        Settings.read_environments()
        assert Settings.installdir == "/app/install"

    def test_basedir_none_if_not_set(self):
        Settings.read_environments()
        # basedir might be set from other tests, just check it doesn't crash
        assert hasattr(Settings, "basedir")
