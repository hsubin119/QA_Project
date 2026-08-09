"""운영 장애 정보를 회귀 테스트 시나리오로 변환하는 프로토타입."""

from typing import Any

__all__ = ["generate_tests"]


def generate_tests(incident: dict[str, Any]) -> dict[str, Any]:
    """Expose the generator without preloading the CLI module."""
    from .incident_to_test import generate_tests as _generate_tests

    return _generate_tests(incident)
