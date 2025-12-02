"""
Reservoir router for applying operational rules to NEWAVE/DECOMP cases.

This module provides endpoints for applying reservoir rules:
- POST /reservoir/ (V1 - legacy) - Uses base62-encoded paths
- POST /reservoir/v2/ (V2 - modern) - Uses S3 bucket + execution_hash
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Annotated

from app.internal.httpresponse import HTTPResponse
from app.models.reservoirrulesrequest import (
    ReservoirRulesRequest,
    ReservoirRulesRequestV2,
)
from app.models.reservoirrulesresponse import (
    ReservoirRulesResponse,
    ReservoirRulesResponseV2,
)
from app.models.errors import ErrorResponse
from app.models.program import Program

from app.adapters.uriparserrepository import AbstractURIParsingRepository
from app.services.unitofwork import (
    factory as uow_factory,
    S3DecompUnitOfWork,
    S3NewaveUnitOfWork,
    S3DecompProspectionUnitOfWork,
    S3DecompUnitOfWorkSync,
    S3NewaveUnitOfWorkSync,
    S3DecompProspectionSync,
)

from app.internal.dependencies import uriParser, get_s3_repo, S3RepoDep
from app.internal.exceptions import (
    ArtifactNotFoundError,
    ParseError,
    RuleApplicationError,
    S3OperationError,
)
from app.adapters.reservoirrulerepository import factory as reservoir_factory
from app.adapters.s3_repository import S3Repository
from app.utils.log import Log

router = APIRouter(
    prefix="/reservoir",
    tags=["Reservoir"],
)


# =============================================================================
# V1 Endpoint (Legacy - base62 paths)
# =============================================================================

responses_v1 = {
    201: {"detail": ""},
    202: {"detail": ""},
    404: {"detail": ""},
    500: {"detail": ""},
    503: {"detail": ""},
}


@router.post(
    "/",
    response_model=ReservoirRulesResponse,
    responses=responses_v1,
    summary="Apply reservoir rules (V1 - Legacy)",
    description="Legacy endpoint using base62-encoded paths. Use /reservoir/v2/ for new integrations.",
    deprecated=True,
)
async def reservoir(
    req: ReservoirRulesRequest,
    uriParser: AbstractURIParsingRepository = Depends(uriParser),
):
    """
    Apply reservoir rules to a case (legacy endpoint).

    This endpoint uses base62-encoded filesystem paths and is deprecated.
    Use POST /reservoir/v2/ with S3 bucket and execution_hash instead.
    """
    sources_paths = [uriParser.parse(s.id) for s in req.sources]
    destination_path = uriParser.parse(req.destination.id)
    for s in sources_paths:
        if isinstance(s, HTTPResponse):
            raise HTTPException(status_code=s.code, detail=s.detail)
    if isinstance(destination_path, HTTPResponse):
        raise HTTPException(
            status_code=destination_path.code, detail=destination_path.detail
        )
    sources_uow = [
        uow_factory(s.program, p) for s, p in zip(req.sources, sources_paths)
    ]
    destination_uow = uow_factory(req.destination.program, destination_path)
    reservoir_repo = reservoir_factory(req.destination.program)
    result = await reservoir_repo.apply(req.rules, sources_uow, destination_uow)
    if isinstance(result, HTTPResponse):
        raise HTTPException(status_code=result.code, detail=result.detail)
    return ReservoirRulesResponse(result=result)


# =============================================================================
# V2 Endpoint (Modern - S3 integration)
# =============================================================================

responses_v2 = {
    200: {"model": ReservoirRulesResponseV2},
    404: {"model": ErrorResponse, "description": "Artifact not found in S3"},
    422: {"model": ErrorResponse, "description": "Failed to parse NEWAVE/DECOMP files"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}


@router.post(
    "/v2/",
    response_model=ReservoirRulesResponseV2,
    responses=responses_v2,
    summary="Apply reservoir rules (V2 - S3)",
    description="Modern endpoint using S3 bucket and execution_hash references.",
)
async def apply_reservoir_rules_v2(
    req: ReservoirRulesRequestV2,
    s3_repo: S3RepoDep,
):
    """
    Apply reservoir rules to a case stored in S3.

    This endpoint:
    1. Downloads source case(s) from S3 for reservoir storage prospection
    2. Downloads destination case from S3
    3. Applies reservoir rules based on storage levels
    4. Uploads modified deck back to S3

    The rules are applied based on the reservoir storage levels from the
    source DECOMP case(s), modifying the destination NEWAVE or DECOMP files.
    """
    dest = req.destination

    try:
        # Prepare source references for prospection
        source_refs = [(s.bucket, s.execution_hash) for s in req.sources]
        Log.log().info(f"Processing {len(source_refs)} source(s) for prospection")

        # Download and process sources for prospection data
        async with S3DecompProspectionUnitOfWork(s3_repo, source_refs) as sources_uow:
            Log.log().info(f"Downloaded {len(sources_uow.repositories)} source case(s)")

            # Create sync wrappers for source repositories
            sources_sync = [
                S3DecompProspectionSync(repo, temp_dir)
                for repo, temp_dir in zip(
                    sources_uow.repositories,
                    sources_uow._temp_dirs,
                )
            ]

            # Select appropriate UoW class for destination
            if dest.program == Program.DECOMP:
                DestUowClass = S3DecompUnitOfWork
            else:
                DestUowClass = S3NewaveUnitOfWork

            # Download and process destination
            async with DestUowClass(
                s3_repo,
                dest.bucket,
                dest.execution_hash,
                dest.output_prefix,
            ) as dest_uow:
                Log.log().info(f"Downloaded destination case: {dest.execution_hash}")

                # Create sync wrapper for destination
                if dest.program == Program.DECOMP:
                    dest_sync = S3DecompUnitOfWorkSync(dest_uow)
                else:
                    dest_sync = S3NewaveUnitOfWorkSync(dest_uow)

                # Get the appropriate rule repository for the destination program
                reservoir_repo = reservoir_factory(dest.program)

                # Apply rules using existing business logic with sync wrappers
                result = await reservoir_repo.apply(
                    req.rules,
                    sources_sync,
                    dest_sync,
                )

                # Check for errors from legacy code
                if isinstance(result, HTTPResponse):
                    if result.code == 404:
                        raise ArtifactNotFoundError(result.detail, {})
                    elif result.code == 422:
                        raise ParseError(result.detail, {})
                    else:
                        raise RuleApplicationError(result.detail, {})

                # Upload modified result to S3
                output_key = await dest_uow.upload_result()
                Log.log().info(f"Uploaded result to s3://{dest.bucket}/{output_key}")

        return ReservoirRulesResponseV2(
            success=True,
            execution_hash=dest.execution_hash,
            output_key=output_key,
            rules_applied=result,
            message=f"Applied {len(result)} reservoir rules",
        )

    except ArtifactNotFoundError as e:
        Log.log().error(f"Artifact not found: {e.message}")
        raise HTTPException(status_code=404, detail=e.to_dict())

    except ParseError as e:
        Log.log().error(f"Parse error: {e.message}")
        raise HTTPException(status_code=422, detail=e.to_dict())

    except RuleApplicationError as e:
        Log.log().error(f"Rule application error: {e.message}")
        raise HTTPException(status_code=500, detail=e.to_dict())

    except S3OperationError as e:
        Log.log().error(f"S3 operation error: {e.message}")
        raise HTTPException(status_code=500, detail=e.to_dict())

    except Exception as e:
        Log.log().exception(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
                "details": None,
            },
        )
