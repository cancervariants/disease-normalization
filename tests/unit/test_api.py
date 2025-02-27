"""Perform basic tests of endpoint branches.
We already have tests and data validation to ensure correctness of the underlying
response objects -- here, we're checking for bad branch logic and for basic assurances
that routes integrate correctly with query methods.
"""

import pytest
from fastapi.testclient import TestClient

from disease.main import app


@pytest.fixture(scope="module")
def api_client():
    """Provide test client fixture."""
    return TestClient(app)


def test_search(api_client):
    """Test /search endpoint."""
    response = api_client.get("/disease/search?q=neuroblastoma")
    assert response.status_code == 200
    assert (
        response.json()["source_matches"]["Mondo"]["records"][0]["concept_id"]
        == "mondo:0005072"
    )

    response = api_client.get("/disease/search?q=neuroblastoma&incl=sdkl")
    assert response.status_code == 422

    response = api_client.get("/disease/search")
    assert response.status_code == 422


def test_normalize(api_client):
    """Test /normalize endpoint."""
    response = api_client.get("/disease/normalize?q=neuroblastoma")
    assert response.status_code == 200
    assert response.json()["disease"]["primaryCode"] == "ncit:C3270"

    response = api_client.get("/disease/normalize")
    assert response.status_code == 422
