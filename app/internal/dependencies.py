"""
FastAPI dependency injection functions.

This module provides dependency factories for use with FastAPI's
Depends() mechanism.
"""

from typing import Annotated

from fastapi import Depends, HTTPException

from app.internal.settings import Settings
from app.adapters.s3_repository import S3Repository, get_s3_repository


# =============================================================================
# S3 Repository Dependency
# =============================================================================


async def get_s3_repo() -> S3Repository:
    """
    Get S3 repository dependency.

    Returns the singleton S3Repository configured from Settings.

    Returns:
        S3Repository instance

    Example:
        @router.post("/")
        async def endpoint(s3: Annotated[S3Repository, Depends(get_s3_repo)]):
            await s3.download_file(...)
    """
    return get_s3_repository()


# Type alias for cleaner dependency injection
S3RepoDep = Annotated[S3Repository, Depends(get_s3_repo)]


# =============================================================================
# Legacy Dependencies (kept for backward compatibility)
# =============================================================================

from app.adapters.uriparserrepository import AbstractURIParsingRepository
from app.adapters.uriparserrepository import factory as parser_factory


async def uriParser() -> AbstractURIParsingRepository:
    """
    Legacy URI parser dependency.

    Deprecated: Use S3 repository with bucket/execution_hash instead.
    """
    s = parser_factory(Settings.uri_pattern)
    if s is None:
        raise HTTPException(500, f"URI pattern {Settings.uri_pattern} not supported")
    return s
