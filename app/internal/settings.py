"""Application settings loaded from environment variables."""

import os
from typing import Optional


class Settings:
    """
    Application settings loaded from environment variables.
    
    Call `read_environments()` to load settings from environment.
    Settings can be overridden for different environments (dev, prod).
    """
    
    # Application
    host: str = "0.0.0.0"
    port: int = 8000
    root_path: str = "/api/v1/rules"
    log_level: str = "INFO"
    
    # Paths (legacy, kept for backward compatibility)
    basedir: Optional[str] = None
    installdir: Optional[str] = None
    uri_pattern: str = "BASE62"  # Legacy: URI parsing pattern
    
    # S3 Configuration
    aws_region: str = "us-east-1"
    s3_endpoint_url: Optional[str] = None  # None for real AWS, URL for LocalStack
    default_newave_bucket: str = "newave-bucket"
    default_decomp_bucket: str = "decomp-bucket"
    
    # Processing
    temp_dir: str = "/tmp/regras-operativas"
    zip_compression_level: int = 6
    max_temp_dir_age_hours: int = 24

    @classmethod
    def read_environments(cls) -> None:
        """Load settings from environment variables."""
        # Application
        cls.host = os.getenv("HOST", "0.0.0.0")
        cls.port = int(os.getenv("PORT", "8000"))
        cls.root_path = os.getenv("ROOT_PATH", "/api/v1/rules")
        cls.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Paths (legacy)
        cls.basedir = os.getenv("APP_BASEDIR")
        cls.installdir = os.getenv("APP_INSTALLDIR")
        cls.uri_pattern = os.getenv("URI_PATTERN", "BASE62")
        
        # S3 Configuration
        cls.aws_region = os.getenv("AWS_REGION", "us-east-1")
        cls.s3_endpoint_url = os.getenv("S3_ENDPOINT_URL") or None
        cls.default_newave_bucket = os.getenv("DEFAULT_NEWAVE_BUCKET", "newave-bucket")
        cls.default_decomp_bucket = os.getenv("DEFAULT_DECOMP_BUCKET", "decomp-bucket")
        
        # Processing
        cls.temp_dir = os.getenv("TEMP_DIR", "/tmp/regras-operativas")
        cls.zip_compression_level = int(os.getenv("ZIP_COMPRESSION_LEVEL", "6"))
        cls.max_temp_dir_age_hours = int(os.getenv("MAX_TEMP_DIR_AGE_HOURS", "24"))
