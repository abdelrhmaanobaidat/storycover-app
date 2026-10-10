import pytest
from fastapi.testclient import TestClient

from storycover.main import app


@pytest.fixture
def client():
    return TestClient(app)
