import json
from collections import Counter
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.config import Settings
from app.extractor import ExtractionError
from app.schemas import Order
from eval.run_eval import DatasetRow, FIELDS, evaluate, load_dataset, main, render_report


def row_json(**fields: object) -> str:
    expected = Order(is_order=True).model_dump(include=set(FIELDS))
    expected.update(fields)
    return json.dumps({"message": "পরীক্ষা পণ্য চাই", "expected": expected}, ensure_ascii=False)


def test_load_unicode_bom_and_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text(row_json() + "\n\n" + row_json(is_order=False), encoding="utf-8-sig")
    rows = load_dataset(path)
    assert len(rows) == 2
    assert rows[0].message == "পরীক্ষা পণ্য চাই"
    assert rows[0].expected.quantity is None
    assert rows[1].expected.is_order is False


@pytest.mark.parametrize("content", ["", "\n \n", "not json", "[]", row_json(quantity=0), row_json(phone="00000"), '{"message":"test","expected":{"is_order":true}}'])
def test_invalid_datasets_rejected(tmp_path: Path, content: str) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_dataset(path)


def test_bad_row_reports_line_number(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text(row_json() + "\n\n{invalid}", encoding="utf-8")
    with pytest.raises(ValueError, match="line 3"):
        load_dataset(path)


def test_hand_calculated_scores_include_nulls_and_non_orders() -> None:
    rows = [
        DatasetRow(message="TEST_PRODUCT 2 ta chai", expected=Order(is_order=True, product="TEST_PRODUCT", quantity=2)),
        DatasetRow(message="hello", expected=Order(is_order=False)),
    ]
    extractor = Mock(side_effect=[Order(is_order=True, product="TEST_PRODUCT", quantity=3), Order(is_order=False)])
    result = evaluate(rows, extractor)
    assert result["overall_accuracy"] == 0.5
    assert result["field_accuracy"]["quantity"] == 0.5
    assert result["mean_field_accuracy"] == pytest.approx(13 / 14)
    assert result["correct_by_field"]["phone"] == 2
    assert result["errors"] == 0
    assert result["failures"][0]["mismatched_fields"] == ["quantity"]
    assert extractor.call_count == 2


def test_errors_are_counted_and_remaining_cases_run() -> None:
    rows = [DatasetRow(message="test", expected=Order(is_order=True))] * 2
    result = evaluate(rows, Mock(side_effect=[ExtractionError("FAKE_SECRET"), Order(is_order=True)]))
    assert result["errors"] == 1
    assert result["overall_accuracy"] == 0.5
    assert set(result["field_accuracy"].values()) == {0.5}
    assert "FAKE_SECRET" not in json.dumps(result)
    assert result["failures"][0]["actual"] is None


def test_exact_comparison_does_not_hide_text_differences() -> None:
    row = DatasetRow(message="TEST_PRODUCT chai", expected=Order(is_order=True, product="TEST_PRODUCT"))
    result = evaluate([row], lambda _: Order(is_order=True, product="test_product"))
    assert result["overall_accuracy"] == 0
    assert result["field_accuracy"]["product"] == 0


def test_warnings_are_not_scored() -> None:
    row = DatasetRow(message="test", expected=Order(is_order=True))
    result = evaluate([row], lambda _: Order(is_order=True, warnings=["Invalid phone"]))
    assert result["overall_accuracy"] == 1
    assert result["failures"] == []
    report = render_report(result, "test-provider", "test-model", Path("dataset.jsonl"))
    assert "100.00%" in report
    assert "None." in report


def test_empty_evaluation_cannot_produce_score() -> None:
    with pytest.raises(ValueError, match="empty"):
        evaluate([], Mock())


def test_cli_writes_failure_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dataset = tmp_path / "dataset.jsonl"
    output = tmp_path / "results.md"
    dataset.write_text(row_json(quantity=2), encoding="utf-8")
    settings = Settings(provider="gemini", model="test-model", api_key="FAKE_SECRET")
    with patch("eval.run_eval.load_settings", return_value=settings):
        with patch("eval.run_eval.extract_order", return_value=Order(is_order=True, quantity=1)):
            assert main(["--dataset", str(dataset), "--output", str(output)]) == 0
    report = output.read_text(encoding="utf-8")
    assert "0.00% (0/1)" in report
    assert "Case 1" in report
    assert "পরীক্ষা পণ্য চাই" in report
    assert '"quantity": 2' in report
    assert '"quantity": 1' in report
    assert "FAKE_SECRET" not in report
    assert "Evaluated 1 messages" in capsys.readouterr().out


def test_invalid_dataset_does_not_call_provider_or_replace_report(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.jsonl"
    output = tmp_path / "results.md"
    dataset.write_text(row_json() + "\ninvalid", encoding="utf-8")
    output.write_text("previous report", encoding="utf-8")
    with patch("eval.run_eval.extract_order") as extractor:
        assert main(["--dataset", str(dataset), "--output", str(output)]) == 1
    extractor.assert_not_called()
    assert output.read_text(encoding="utf-8") == "previous report"


def test_all_provider_failures_save_zero_score_and_return_error(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.jsonl"
    output = tmp_path / "results.md"
    dataset.write_text(row_json(), encoding="utf-8")
    settings = Settings(provider="gemini", model="test-model", api_key="FAKE_SECRET")
    with patch("eval.run_eval.load_settings", return_value=settings):
        with patch("eval.run_eval.extract_order", side_effect=ExtractionError("FAKE_SECRET")):
            assert main(["--dataset", str(dataset), "--output", str(output)]) == 1
    report = output.read_text(encoding="utf-8")
    assert "Extraction errors: 1" in report
    assert "0.00% (0/1)" in report
    assert "FAKE_SECRET" not in report


def test_output_cannot_overwrite_dataset(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text(row_json(), encoding="utf-8")
    assert main(["--dataset", str(path), "--output", str(path)]) == 1
    assert path.read_text(encoding="utf-8") == row_json()


def test_dataset_metadata_loads_and_appears_in_failures(tmp_path: Path) -> None:
    data = json.loads(row_json())
    data.update(id="msg_test", category="messy")
    path = tmp_path / "dataset.jsonl"
    path.write_text(json.dumps(data), encoding="utf-8")
    rows = load_dataset(path)
    for extractor in (Mock(return_value=Order(is_order=False)), Mock(side_effect=ExtractionError("test error"))):
        result = evaluate(rows, extractor)
        failure = result["failures"][0]
        assert failure["id"] == "msg_test"
        assert failure["category"] == "messy"
        report = render_report(result, "test", "test", path)
        assert '"id": "msg_test"' in report


def test_metadata_does_not_allow_arbitrary_extra_keys(tmp_path: Path) -> None:
    data = json.loads(row_json())
    data["unexpected"] = "value"
    path = tmp_path / "dataset.jsonl"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        load_dataset(path)


def test_supplied_dataset_is_complete_and_uses_synthetic_labels() -> None:
    path = Path(__file__).resolve().parents[2] / "eval" / "dataset.jsonl"
    rows = load_dataset(path)
    assert len(rows) == 50
    assert len({row.id for row in rows}) == 50
    assert Counter(row.category for row in rows) == {
        "clean": 15, "messy": 15, "mixed": 10, "missing": 5, "non_order": 5,
    }
    for row in rows:
        assert row.expected.notes is None
        for field, prefixes in (
            ("customer_name", ("TEST_CUSTOMER_", "পরীক্ষা_ক্রেতা_")),
            ("address", ("TEST_ADDRESS_", "পরীক্ষা_ঠিকানা_")),
        ):
            value = getattr(row.expected, field)
            if value is not None:
                assert value.startswith(prefixes)
                assert value in row.message
