from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass
class StockApiClient:
    base_url: str

    def get_stock(self, product_id: str) -> requests.Response:
        return requests.get(
            f"{self.base_url}/v1/products/{product_id}/stock",
            timeout=2,
        )

    def create_order(self, product_id: str, quantity: int) -> requests.Response:
        return requests.post(
            f"{self.base_url}/v1/orders",
            json={"productId": product_id, "quantity": quantity},
            timeout=2,
        )

    def cancel_order(self, order_id: str) -> requests.Response:
        return requests.post(
            f"{self.base_url}/v1/orders/{order_id}/cancel",
            json={},
            timeout=2,
        )


def assert_stock(
    client: StockApiClient,
    product_id: str,
    expected_stock: int,
    *,
    sold_out: bool,
) -> None:
    response = client.get_stock(product_id)
    assert response.status_code == 200
    assert response.json() == {
        "productId": product_id,
        "stock": expected_stock,
        "soldOut": sold_out,
    }


def assert_api_error(
    response: requests.Response,
    expected_status: int,
    expected_code: str,
) -> None:
    assert response.status_code == expected_status
    payload = response.json()
    assert payload["error"]["code"] == expected_code
    assert payload["error"]["message"]
