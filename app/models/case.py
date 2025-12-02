"""
Case reference models for S3-based case storage.

This module provides models for referencing cases stored in S3,
replacing the legacy base62-encoded filesystem paths.
"""

from pydantic import BaseModel, Field

from app.models.program import Program


class Case(BaseModel):
    """
    Legacy class for defining a case reference (backward compatibility).

    Deprecated: Use CaseReference for new code.
    """

    id: str
    program: Program


class CaseReference(BaseModel):
    """
    Reference to a case stored in S3.

    Replaces the base62-encoded filesystem path with explicit
    S3 bucket and execution hash.

    Attributes:
        bucket: S3 bucket name containing the case artifacts
        execution_hash: Unique identifier for the execution
        program: Program type (NEWAVE or DECOMP)
        output_prefix: S3 prefix for output files (default: "ingest")

    Example:
        >>> ref = CaseReference(
        ...     bucket="decomp-bucket",
        ...     execution_hash="abc123def456",
        ...     program="DECOMP"
        ... )
        >>> ref.input_deck_key
        'artifacts/abc123def456/entradas/deck_processado.zip'
    """

    bucket: str = Field(
        ...,
        description="S3 bucket name",
        examples=["decomp-bucket", "newave-bucket"],
    )
    execution_hash: str = Field(
        ...,
        description="Unique execution identifier",
        min_length=1,
        examples=["abc123def456"],
    )
    program: Program = Field(
        ...,
        description="Program type (NEWAVE or DECOMP)",
    )
    output_prefix: str = Field(
        default="ingest",
        description="S3 prefix for output files",
    )

    @property
    def input_deck_key(self) -> str:
        """S3 key for input deck zip."""
        return f"artifacts/{self.execution_hash}/entradas/deck_processado.zip"

    def get_output_key(self, suffix: str = "_regras.zip") -> str:
        """
        Get S3 key for output zip.

        Args:
            suffix: File suffix (default: "_regras.zip")

        Returns:
            Full S3 key for output file
        """
        return f"{self.output_prefix}/{self.execution_hash}{suffix}"

    def get_relato_key(self, extension: str) -> str:
        """
        Get S3 key for relato file (DECOMP only).

        Args:
            extension: File extension (e.g., "rv0")

        Returns:
            Full S3 key for relato file
        """
        return f"artifacts/{self.execution_hash}/saidas/relato.{extension}"
