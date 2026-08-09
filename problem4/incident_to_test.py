"""Generate reviewable regression-test drafts from confirmed incidents."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TestScenario:
    name: str
    priority: str
    purpose: str
    layer: str
    given: list[str]
    when: list[str]
    then: list[str]


SUPPORTED_ROOT_CAUSES = {
    "RACE_CONDITION",
    "STATE_TRANSITION",
    "IDEMPOTENCY",
    "DATA_CONSISTENCY",
    "TIMEOUT",
}

REQUIRED_FIELDS = (
    "incidentId",
    "expectedBehavior",
    "actualBehavior",
    "rootCause",
)


def _missing_fields(incident: dict[str, Any]) -> list[str]:
    return [field for field in REQUIRED_FIELDS if not incident.get(field)]


def _race_condition_scenarios() -> list[TestScenario]:
    return [
        TestScenario(
            name="마지막 재고 동시 주문 시 하나의 주문만 성공",
            priority="P0",
            purpose="REPRODUCTION",
            layer="INTEGRATION",
            given=[
                "상품 재고가 1개다",
                "서로 다른 고객 두 명이 존재한다",
            ],
            when=["두 고객이 같은 상품을 동시에 주문한다"],
            then=[
                "주문 1건만 성공한다",
                "나머지 주문은 OUT_OF_STOCK으로 실패한다",
                "최종 재고는 0이다",
                "재고가 음수가 되지 않는다",
            ],
        ),
        TestScenario(
            name="성공 주문 취소 후 재고 복구",
            priority="P0",
            purpose="FIX_VERIFICATION",
            layer="API",
            given=[
                "마지막 재고 주문 1건이 성공했다",
                "다른 주문은 품절로 실패했다",
            ],
            when=["성공한 주문을 취소한다"],
            then=[
                "재고가 1개로 복구된다",
                "품절 상태가 해제된다",
            ],
        ),
        TestScenario(
            name="실패 주문 취소 요청 시 재고 미변경",
            priority="P1",
            purpose="DERIVED",
            layer="API",
            given=["재고 부족으로 실패한 주문이 존재한다"],
            when=["실패 주문에 대해 취소를 요청한다"],
            then=[
                "취소 요청이 거절된다",
                "재고 수량이 변경되지 않는다",
            ],
        ),
    ]


def generate_tests(incident: dict[str, Any]) -> dict[str, Any]:
    """Return test drafts only when the incident has a confirmed root cause."""
    missing = _missing_fields(incident)
    if missing:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "필수 장애 정보가 부족합니다.",
            "missingInformation": missing,
            "tests": [],
        }

    root_cause = incident["rootCause"]
    if not isinstance(root_cause, dict):
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "rootCause는 category와 confirmed를 포함해야 합니다.",
            "missingInformation": ["rootCause.category", "rootCause.confirmed"],
            "tests": [],
        }

    category = root_cause.get("category")
    if root_cause.get("confirmed") is not True:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "근본 원인이 확정되지 않았습니다.",
            "missingInformation": ["확정된 근본 원인"],
            "tests": [],
        }

    if category not in SUPPORTED_ROOT_CAUSES:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "지원하지 않는 근본 원인입니다.",
            "missingInformation": ["지원 가능한 근본 원인 분류"],
            "tests": [],
        }

    if category != "RACE_CONDITION":
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "현재 프로토타입은 RACE_CONDITION 코드 생성을 지원합니다.",
            "incidentId": incident["incidentId"],
            "rootCause": category,
            "missingInformation": ["해당 장애 유형의 생성 전략"],
            "tests": [],
        }

    scenarios = _race_condition_scenarios()
    return {
        "status": "DRAFT_CREATED",
        "incidentId": incident["incidentId"],
        "rootCause": category,
        "tests": [asdict(scenario) for scenario in scenarios],
        "reviewRequired": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="운영 장애 기반 회귀 테스트 시나리오 생성기",
    )
    parser.add_argument("incident", type=Path)
    args = parser.parse_args()

    incident = json.loads(args.incident.read_text(encoding="utf-8"))
    result = generate_tests(incident)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
