from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import perf_counter, sleep

from Test2.bmart_stock import InventoryStore
from Test2.tests.helpers import StockApiClient, assert_api_error, assert_stock


def test_get_stock_returns_current_quantity(
    api_client: StockApiClient,
    seeded_product: str,
) -> None:
    assert_stock(api_client, seeded_product, 10, sold_out=False)


def test_get_unknown_product_returns_404(api_client: StockApiClient) -> None:
    assert_api_error(
        api_client.get_stock("unknown"),
        expected_status=404,
        expected_code="PRODUCT_NOT_FOUND",
    )


def test_cart_style_repeated_reads_do_not_deduct_stock(
    api_client: StockApiClient,
    seeded_product: str,
) -> None:
    api_client.get_stock(seeded_product)
    api_client.get_stock(seeded_product)

    assert_stock(api_client, seeded_product, 10, sold_out=False)


def test_paid_order_deducts_stock(
    api_client: StockApiClient,
    seeded_product: str,
) -> None:
    response = api_client.create_order(seeded_product, quantity=1)

    assert response.status_code == 201
    assert response.json()["remainingStock"] == 9
    assert response.json()["status"] == "PAID"
    assert_stock(api_client, seeded_product, 9, sold_out=False)


def test_order_can_deduct_multiple_units(
    api_client: StockApiClient,
    seeded_product: str,
) -> None:
    response = api_client.create_order(seeded_product, quantity=4)

    assert response.status_code == 201
    assert response.json()["quantity"] == 4
    assert_stock(api_client, seeded_product, 6, sold_out=False)


def test_insufficient_stock_rejects_order_without_changing_stock(
    api_client: StockApiClient,
    store: InventoryStore,
) -> None:
    store.seed_product("last-two", stock=2)

    assert_api_error(
        api_client.create_order("last-two", quantity=3),
        expected_status=409,
        expected_code="OUT_OF_STOCK",
    )
    assert_stock(api_client, "last-two", 2, sold_out=False)


def test_zero_quantity_is_rejected(
    api_client: StockApiClient,
    seeded_product: str,
) -> None:
    assert_api_error(
        api_client.create_order(seeded_product, quantity=0),
        expected_status=400,
        expected_code="INVALID_QUANTITY",
    )


def test_unknown_product_order_is_rejected(api_client: StockApiClient) -> None:
    assert_api_error(
        api_client.create_order("unknown", quantity=1),
        expected_status=404,
        expected_code="PRODUCT_NOT_FOUND",
    )


def test_cancel_restores_deducted_stock(
    api_client: StockApiClient,
    seeded_product: str,
) -> None:
    order = api_client.create_order(seeded_product, quantity=3).json()

    response = api_client.cancel_order(order["orderId"])

    assert response.status_code == 200
    assert response.json()["restoredQuantity"] == 3
    assert response.json()["status"] == "CANCELLED"
    assert_stock(api_client, seeded_product, 10, sold_out=False)


def test_cancel_unknown_order_returns_404(api_client: StockApiClient) -> None:
    assert_api_error(
        api_client.cancel_order("unknown-order"),
        expected_status=404,
        expected_code="ORDER_NOT_FOUND",
    )


def test_second_cancel_does_not_restore_stock_twice(
    api_client: StockApiClient,
    seeded_product: str,
) -> None:
    order_id = api_client.create_order(seeded_product, quantity=2).json()["orderId"]

    assert api_client.cancel_order(order_id).status_code == 200
    assert_api_error(
        api_client.cancel_order(order_id),
        expected_status=409,
        expected_code="ALREADY_CANCELLED",
    )
    assert_stock(api_client, seeded_product, 10, sold_out=False)


def test_last_unit_purchase_changes_product_to_sold_out(
    api_client: StockApiClient,
    store: InventoryStore,
) -> None:
    store.seed_product("last-one", stock=1)

    response = api_client.create_order("last-one", quantity=1)

    assert response.status_code == 201
    assert response.json()["soldOut"] is True
    assert_stock(api_client, "last-one", 0, sold_out=True)


def test_cancel_sold_out_order_makes_product_available_again(
    api_client: StockApiClient,
    store: InventoryStore,
) -> None:
    store.seed_product("restock-item", stock=1)
    order_id = api_client.create_order("restock-item", quantity=1).json()["orderId"]

    response = api_client.cancel_order(order_id)

    assert response.status_code == 200
    assert response.json()["soldOut"] is False
    assert_stock(api_client, "restock-item", 1, sold_out=False)


def test_two_near_simultaneous_orders_for_last_unit_allow_only_one_success(
    api_client: StockApiClient,
    store: InventoryStore,
) -> None:
    product_id = "peak-time-item"
    store.seed_product(product_id, stock=1)
    barrier = Barrier(2)

    def place_order(delay_seconds: float) -> tuple[int, str | None, float]:
        barrier.wait(timeout=2)
        sleep(delay_seconds)
        started_at = perf_counter()
        response = api_client.create_order(product_id, quantity=1)
        error_code = (
            response.json().get("error", {}).get("code")
            if response.status_code != 201
            else None
        )
        return response.status_code, error_code, started_at

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(place_order, (0.0, 0.02)))

    request_interval = abs(results[0][2] - results[1][2])
    assert 0.015 <= request_interval <= 0.1
    assert sorted(status for status, _, _ in results) == [201, 409]
    assert [code for _, code, _ in results if code] == ["OUT_OF_STOCK"]
    assert_stock(api_client, product_id, 0, sold_out=True)
