from __future__ import annotations

from problem4 import generate_tests


def incident(**overrides: object) -> dict:
    value = {
        "incidentId": "INC-2026-0142",
        "expectedBehavior": "재고 1개일 때 주문 1건만 성공",
        "actualBehavior": "두 주문이 성공하고 재고가 -1",
        "rootCause": {
            "category": "RACE_CONDITION",
            "confirmed": True,
        },
    }
    value.update(overrides)
    return value


def test_missing_incident_information_requires_review() -> None:
    result = generate_tests({"incidentId": "INC-1"})

    assert result["status"] == "REVIEW_REQUIRED"
    assert set(result["missingInformation"]) == {
        "expectedBehavior",
        "actualBehavior",
        "rootCause",
    }
    assert result["tests"] == []


def test_unconfirmed_root_cause_does_not_generate_tests() -> None:
    result = generate_tests(
        incident(
            rootCause={
                "category": "RACE_CONDITION",
                "confirmed": False,
            }
        )
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["tests"] == []


def test_unsupported_root_cause_requires_review() -> None:
    result = generate_tests(
        incident(
            rootCause={
                "category": "UNKNOWN",
                "confirmed": True,
            }
        )
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["tests"] == []


def test_race_condition_generates_reproduction_and_follow_up_tests() -> None:
    result = generate_tests(incident())

    assert result["status"] == "DRAFT_CREATED"
    assert result["reviewRequired"] is True
    assert len(result["tests"]) == 3
    assert {test["purpose"] for test in result["tests"]} == {
        "REPRODUCTION",
        "FIX_VERIFICATION",
        "DERIVED",
    }


def test_reproduction_scenario_checks_overselling_invariants() -> None:
    result = generate_tests(incident())
    reproduction = next(
        test
        for test in result["tests"]
        if test["purpose"] == "REPRODUCTION"
    )

    assert reproduction["priority"] == "P0"
    assert reproduction["layer"] == "INTEGRATION"
    assert "주문 1건만 성공한다" in reproduction["then"]
    assert "최종 재고는 0이다" in reproduction["then"]
    assert "재고가 음수가 되지 않는다" in reproduction["then"]
