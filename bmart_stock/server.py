"""Thread-safe in-memory implementation of the B마트 stock API."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import RLock, Thread
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4


class ApiError(Exception):
    """Domain error converted to a JSON HTTP response."""

    def __init__(self, status: HTTPStatus, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


@dataclass
class Product:
    product_id: str
    stock: int

    @property
    def sold_out(self) -> bool:
        return self.stock == 0


@dataclass
class Order:
    order_id: str
    product_id: str
    quantity: int
    status: str = "PAID"


class InventoryStore:
    """Keeps products and orders consistent inside one critical section."""

    def __init__(self) -> None:
        self._products: dict[str, Product] = {}
        self._orders: dict[str, Order] = {}
        self._lock = RLock()

    def seed_product(self, product_id: str, stock: int) -> None:
        if not product_id or stock < 0:
            raise ValueError("product_id is required and stock must be non-negative")
        with self._lock:
            self._products[product_id] = Product(product_id, stock)

    def get_stock(self, product_id: str) -> dict[str, Any]:
        with self._lock:
            product = self._get_product(product_id)
            return self._stock_payload(product)

    def create_order(self, product_id: str, quantity: int) -> dict[str, Any]:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "INVALID_QUANTITY",
                "quantity must be a positive integer",
            )

        # The availability check and deduction must remain atomic. The
        # concurrency test would expose an oversell if this lock were removed.
        with self._lock:
            product = self._get_product(product_id)
            if product.stock < quantity:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "OUT_OF_STOCK",
                    "not enough stock",
                )

            product.stock -= quantity
            order = Order(str(uuid4()), product_id, quantity)
            self._orders[order.order_id] = order
            return {
                "orderId": order.order_id,
                "productId": order.product_id,
                "quantity": order.quantity,
                "status": order.status,
                "remainingStock": product.stock,
                "soldOut": product.sold_out,
            }

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise ApiError(
                    HTTPStatus.NOT_FOUND,
                    "ORDER_NOT_FOUND",
                    "order does not exist",
                )
            if order.status == "CANCELLED":
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "ALREADY_CANCELLED",
                    "order is already cancelled",
                )

            product = self._get_product(order.product_id)
            product.stock += order.quantity
            order.status = "CANCELLED"
            return {
                "orderId": order.order_id,
                "status": order.status,
                "restoredQuantity": order.quantity,
                "currentStock": product.stock,
                "soldOut": product.sold_out,
            }

    def _get_product(self, product_id: str) -> Product:
        product = self._products.get(product_id)
        if product is None:
            raise ApiError(
                HTTPStatus.NOT_FOUND,
                "PRODUCT_NOT_FOUND",
                "product does not exist",
            )
        return product

    @staticmethod
    def _stock_payload(product: Product) -> dict[str, Any]:
        return {
            "productId": product.product_id,
            "stock": product.stock,
            "soldOut": product.sold_out,
        }


class _StockApiServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], store: InventoryStore) -> None:
        super().__init__(address, StockApiHandler)
        self.store = store


class StockApiHandler(BaseHTTPRequestHandler):
    server: _StockApiServer

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            segments = self._segments()
            if len(segments) == 4 and segments[:2] == ["v1", "products"] and segments[3] == "stock":
                self._send(HTTPStatus.OK, self.server.store.get_stock(segments[2]))
                return
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "endpoint does not exist")
        except ApiError as error:
            self._send_error(error)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            segments = self._segments()
            if segments == ["v1", "orders"]:
                body = self._read_json()
                product_id = body.get("productId")
                if not isinstance(product_id, str) or not product_id:
                    raise ApiError(
                        HTTPStatus.BAD_REQUEST,
                        "INVALID_PRODUCT_ID",
                        "productId is required",
                    )
                result = self.server.store.create_order(
                    product_id,
                    body.get("quantity"),
                )
                self._send(HTTPStatus.CREATED, result)
                return

            if len(segments) == 4 and segments[:2] == ["v1", "orders"] and segments[3] == "cancel":
                self._read_json(allow_empty=True)
                self._send(
                    HTTPStatus.OK,
                    self.server.store.cancel_order(segments[2]),
                )
                return
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "endpoint does not exist")
        except ApiError as error:
            self._send_error(error)

    def _segments(self) -> list[str]:
        return [part for part in urlparse(self.path).path.split("/") if part]

    def _read_json(self, allow_empty: bool = False) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0 and allow_empty:
            return {}
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "INVALID_JSON",
                "request body must be valid JSON",
            ) from None
        if not isinstance(payload, dict):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "INVALID_JSON",
                "request body must be a JSON object",
            )
        return payload

    def _send_error(self, error: ApiError) -> None:
        self._send(
            error.status,
            {"error": {"code": error.code, "message": error.message}},
        )

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class StubServer:
    """Lifecycle wrapper used by tests and by the command-line entry point."""

    def __init__(
        self,
        store: InventoryStore | None = None,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self.store = store or InventoryStore()
        self._server = _StockApiServer((host, port), self.store)
        self._thread: Thread | None = None

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def start(self) -> "StubServer":
        if self._thread is None:
            self._thread = Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
        return self

    def stop(self) -> None:
        if self._thread is not None:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join(timeout=5)
            self._thread = None


def main() -> None:
    parser = argparse.ArgumentParser(description="B마트 재고 API Stub 서버")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--product-id", default="popular-product")
    parser.add_argument("--stock", type=int, default=10)
    args = parser.parse_args()

    store = InventoryStore()
    store.seed_product(args.product_id, args.stock)
    server = StubServer(store, args.host, args.port).start()
    print(f"Stub server: {server.base_url}")
    print(f"Seed product: {args.product_id} (stock={args.stock})")
    try:
        assert server._thread is not None
        server._thread.join()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
