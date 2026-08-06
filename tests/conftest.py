from __future__ import annotations

from collections.abc import Iterator

import pytest

from bmart_stock import InventoryStore, StubServer
from tests.helpers import StockApiClient


@pytest.fixture
def store() -> InventoryStore:
    return InventoryStore()


@pytest.fixture
def api_client(store: InventoryStore) -> Iterator[StockApiClient]:
    server = StubServer(store).start()
    try:
        yield StockApiClient(server.base_url)
    finally:
        server.stop()


@pytest.fixture
def seeded_product(store: InventoryStore) -> str:
    product_id = "milk-1l"
    store.seed_product(product_id, stock=10)
    return product_id
