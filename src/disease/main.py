"""Main application for FastAPI"""

import html
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from enum import Enum
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request

from disease import __version__
from disease.config import config
from disease.database.database import create_db
from disease.logs import initialize_logs
from disease.query import InvalidParameterException, QueryHandler
from disease.schemas import (
    APP_DESCRIPTION,
    LAB_EMAIL,
    LAB_WEBPAGE_URL,
    NormalizationService,
    SearchService,
    ServiceInfo,
    ServiceOrganization,
    ServiceType,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Perform operations that interact with the lifespan of the FastAPI instance.

    See https://fastapi.tiangolo.com/advanced/events/#lifespan.

    :param app: FastAPI instance
    """
    if config.debug:
        initialize_logs(logging.DEBUG)
    else:
        initialize_logs(logging.INFO)
    db = create_db()
    query_handler = QueryHandler(db)
    app.state.query_handler = query_handler
    yield
    db.close_connection()


app = FastAPI(
    title="VICC Disease Normalizer",
    description=APP_DESCRIPTION,
    version=__version__,
    contact={
        "name": "Alex H. Wagner",
        "email": LAB_EMAIL,
        "url": LAB_WEBPAGE_URL,
    },
    license={
        "name": "MIT",
        "url": "https://github.com/cancervariants/disease_normalization/blob/main/LICENSE",
    },
    docs_url="/disease",
    openapi_url="/disease/openapi.json",
    swagger_ui_parameters={"tryItOutEnabled": True},
    lifespan=lifespan,
)


class _Tag(str, Enum):
    """Define tag names for endpoints."""

    SEARCH = "Search"
    NORMALIZE = "Normalize"
    META = "Meta"


# endpoint description text
get_matches_summary = "Given query, provide highest matches from " "each source."
search_descr = "Search for disease term."
response_descr = "A response to a validly-formed query."
q_descr = "Disease term to search for."
incl_descr = (
    "Comma-separated list of source names to include in "
    "response. Will exclude all other sources. Will return HTTP "
    "status code 422: Unprocessable Entity if both 'incl' and "
    "'excl' parameters are given."
)
excl_descr = (
    "Comma-separated list of source names to exclude in "
    "response. Will include all other sources. Will return HTTP "
    "status code 422: Unprocessable Entity if both 'incl' and"
    "'excl' parameters are given."
)
normalize_description = (
    "Return merged strongest-match concept for query " "string provided by user."
)


@app.get(
    "/disease/search",
    summary=get_matches_summary,
    description=search_descr,
    operation_id="getQueryResponse",
    response_description=response_descr,
    response_model_exclude_none=True,
    tags=[_Tag.SEARCH],
)
def search(
    request: Request,
    q: Annotated[str, Query(description=q_descr)],
    incl: Annotated[str | None, Query(description=incl_descr)] = "",
    excl: Annotated[str | None, Query(description=excl_descr)] = "",
) -> SearchService:
    """For each source, return strongest-match concepts for query string
    provided by user.

    :param q: disease search term
    :param incl: sources to include
    :param excl: sources to excl
    :return: search results
    """
    query_handler = request.app.state.query_handler
    try:
        response = query_handler.search(html.unescape(q), incl=incl, excl=excl)
    except InvalidParameterException as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return response


merged_matches_summary = "Given query, provide normalized record."
merged_response_descr = "A response to a validly-formed query."
merged_q_descr = "Disease to normalize."


@app.get(
    "/disease/normalize",
    summary=merged_matches_summary,
    operation_id="getQuerymergedResponse",
    response_description=merged_response_descr,
    description=normalize_description,
    response_model_exclude_none=True,
    tags=[_Tag.NORMALIZE],
)
def normalize(
    request: Request,
    q: Annotated[str, Query(description=merged_q_descr)],
) -> NormalizationService:
    """Return strongest-match normalized concept for query string provided by
    user.

    :param q: disease search term
    """
    query_handler = request.app.state.query_handler
    try:
        response = query_handler.normalize(q)
    except InvalidParameterException as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return response


@app.get(
    "/service_info",
    summary="Get basic service information",
    description="Retrieve service metadata, such as versioning and contact info. Structured in conformance with the [GA4GH service info API specification](https://www.ga4gh.org/product/service-info/)",
    tags=[_Tag.META],
)
def service_info() -> ServiceInfo:
    """Provide service info per GA4GH Service Info spec
    :return: conformant service info description
    """
    return ServiceInfo(
        organization=ServiceOrganization(), type=ServiceType(), environment=config.env
    )
