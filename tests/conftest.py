from pathlib import Path
import pytest
from campaign_compass.data import load_directory
from campaign_compass.analytics import facts


@pytest.fixture(scope="session")
def dataset():
    return load_directory(Path(__file__).parents[1] / "data")


@pytest.fixture(scope="session")
def full(dataset):
    return facts(dataset)
