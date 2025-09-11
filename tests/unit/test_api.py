"""Perform basic tests of endpoint branches.
We already have tests and data validation to ensure correctness of the underlying
response objects -- here, we're checking for bad branch logic and for basic assurances
that routes integrate correctly with query methods.
"""

from pathlib import Path

import jsonschema
import pytest
import pytest_asyncio
import yaml
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from disease.main import app


@pytest_asyncio.fixture
async def async_app():
    async with LifespanManager(app) as manager:
        yield manager.app


@pytest_asyncio.fixture
async def api_client(async_app):
    async with AsyncClient(
        transport=ASGITransport(async_app), base_url="http://tests"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_search(api_client: AsyncClient):
    """Test /search endpoint."""
    response = await api_client.get("/disease/search?q=neuroblastoma")
    assert response.status_code == 200
    assert (
        response.json()["source_matches"]["Mondo"]["records"][0]["concept_id"]
        == "mondo:0005072"
    )

    response = await api_client.get("/disease/search?q=neuroblastoma&incl=sdkl")
    assert response.status_code == 422

    response = await api_client.get("/disease/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_normalize(api_client: AsyncClient):
    """Test /normalize endpoint."""
    response = await api_client.get("/disease/normalize?q=neuroblastoma")
    assert response.status_code == 200
    assert response.json()["disease"]["primaryCoding"] == {
        "id": "ncit:C3270",
        "code": "C3270",
        "system": "https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
    }

    response = await api_client.get("/disease/normalize")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_service_info(api_client: AsyncClient, test_data_dir: Path):
    response = await api_client.get("/disease/service-info")
    response.raise_for_status()

    with (test_data_dir / "service_info_openapi.yaml").open() as f:
        spec = yaml.safe_load(f)

    resp_schema = spec["paths"]["/service-info"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]

    resolver = jsonschema.RefResolver.from_schema(spec)
    data = response.json()
    jsonschema.validate(instance=data, schema=resp_schema, resolver=resolver)
