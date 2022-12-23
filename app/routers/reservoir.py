from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.internal.httpresponse import HTTPResponse
from app.models.reservoirrulesrequest import ReservoirRulesRequest
from app.models.reservoirrulesresponse import ReservoirRulesResponse

from app.adapters.uriparserrepository import AbstractURIParsingRepository
from app.services.unitofwork import factory as uow_factory

from app.internal.dependencies import uriParser
from app.adapters.reservoirrulerepository import factory as reservoir_factory

router = APIRouter(
    prefix="/reservoir",
    tags=["reservoir"],
)


responses = {
    201: {"detail": ""},
    202: {"detail": ""},
    404: {"detail": ""},
    500: {"detail": ""},
    503: {"detail": ""},
}


@router.post(
    "/",
    response_model=ReservoirRulesResponse,
    responses=responses,
)
async def reservoir(
    req: ReservoirRulesRequest,
    uriParser: AbstractURIParsingRepository = Depends(uriParser),
):
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
    result = await reservoir_repo.apply(
        req.rules, sources_uow, destination_uow
    )
    if isinstance(result, HTTPResponse):
        raise HTTPException(status_code=result.code, detail=result.detail)
    return ReservoirRulesResponse(result=result)
