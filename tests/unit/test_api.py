"""Perform basic tests of endpoint branches.
We already have tests and data validation to ensure correctness of the underlying
response objects -- here, we're checking for bad branch logic and for basic assurances
that routes integrate correctly with query methods.
"""

import re
from datetime import datetime

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from disease.main import app
from disease.schemas import ServiceEnvironment


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
async def test_service_info(api_client: AsyncClient):
    response = await api_client.get("/service_info")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["id"] == "org.genomicmedlab.disease_normalizer"
    assert response_json["name"] == "disease_normalizer"
    assert response_json["type"]["group"] == "org.genomicmedlab"
    assert response_json["type"]["artifact"] == "Disease Normalizer API"
    expected_version_pattern = (
        r"\d+\.\d+\.?"  # at minimum, should be something like "0.1"
    )
    assert re.match(expected_version_pattern, response_json["type"]["version"])
    assert (
        response_json["description"]
        == "Resolve ambiguous references and descriptions of human diseases to consistently-structured, normalized terms"
    )
    assert response_json["organization"] == {
        "name": "Genomic Medicine Lab at Nationwide Children's Hospital",
        "url": "https://www.nationwidechildrens.org/specialties/institute-for-genomic-medicine/research-labs/wagner-lab",
    }
    assert response_json["contactUrl"] == "Alex.Wagner@nationwidechildrens.org"
    assert (
        response_json["documentationUrl"]
        == "https://disease-normalizer.readthedocs.io/"
    )
    assert datetime.fromisoformat(response_json["createdAt"])
    assert ServiceEnvironment(response_json["environment"])
    assert re.match(expected_version_pattern, response_json["version"])
