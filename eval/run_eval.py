"""Score synthetic JSONL messages against manually labeled expected orders."""

import argparse
import json
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import load_settings
from app.extractor import ExtractionError, extract_order
from app.schemas import Message, Order
from eval.baseline import extract_baseline


FIELDS = ("is_order", "customer_name", "phone", "address", "product", "quantity", "notes")
DIRECTORY = Path(__file__).resolve().parent


class DatasetRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    category: str | None = None
    message: Message
    expected: Order


def load_dataset(path: Path) -> list[DatasetRow]:
    """Validate the entire dataset before any paid extraction requests."""
    rows: list[DatasetRow] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = DatasetRow.model_validate_json(line)
        except ValidationError:
            raise ValueError(f"Invalid dataset row at line {line_number}.") from None
        missing = set(FIELDS) - row.expected.model_fields_set
        if missing:
            raise ValueError(f"Line {line_number}: expected must include {', '.join(sorted(missing))}; use null for missing values.")
        rows.append(row)
    if not rows:
        raise ValueError("Dataset is empty. Add your synthetic labeled messages before running evaluation.")
    return rows


def evaluate(rows: list[DatasetRow], extractor: Callable[[str], Order]) -> dict[str, Any]:
    """Use exact equality; extraction errors count as incorrect for every field."""
    if not rows:
        raise ValueError("Cannot evaluate an empty dataset.")
    correct = dict.fromkeys(FIELDS, 0)
    exact_matches = 0
    errors = 0
    failures: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        expected = row.expected.model_dump(include=set(FIELDS))
        try:
            actual = extractor(row.message).model_dump(include=set(FIELDS))
        except (ExtractionError, ValidationError):
            errors += 1
            failures.append({"case": index, "id": row.id, "category": row.category,
                             "message": row.message, "expected": expected,
                             "actual": None, "error": "Extraction failed; all fields counted as incorrect."})
            continue
        differences = [field for field in FIELDS if actual[field] != expected[field]]
        for field in FIELDS:
            correct[field] += actual[field] == expected[field]
        exact_matches += not differences
        if differences:
            failures.append({"case": index, "id": row.id, "category": row.category,
                             "message": row.message, "expected": expected,
                             "actual": actual, "mismatched_fields": differences})
    total = len(rows)
    return {
        "total": total, "exact_matches": exact_matches, "errors": errors,
        "overall_accuracy": exact_matches / total,
        "field_accuracy": {field: correct[field] / total for field in FIELDS},
        "correct_by_field": correct,
        "mean_field_accuracy": sum(correct.values()) / (total * len(FIELDS)),
        "failures": failures,
    }


def render_report(result: dict[str, Any], provider: str, model: str, dataset: Path) -> str:
    """Render scores and every failure, without recording credentials."""
    lines = [
        "# Evaluation results", "",
        f"Run time (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"Provider: {provider}", f"Model: {model}", f"Dataset: {dataset.name}",
        f"Messages: {result['total']}", f"Extraction errors: {result['errors']}", "",
        f"Overall accuracy (all 7 fields exact): {result['overall_accuracy']:.2%} "
        f"({result['exact_matches']}/{result['total']})",
        f"Mean field accuracy: {result['mean_field_accuracy']:.2%}", "",
        "| Field | Correct / total | Accuracy |", "| --- | --- | --- |",
    ]
    for field in FIELDS:
        lines.append(f"| {field} | {result['correct_by_field'][field]} / {result['total']} | {result['field_accuracy'][field]:.2%} |")
    lines.extend(["", "Exact comparison includes nulls and non-orders. Warnings are not scored.",
                  "Extraction errors count as incorrect for all fields; they are never omitted from denominators.",
                  "Provider errors affect these end-to-end scores, so they are not pure model-accuracy measurements.",
                  "", "## Failures", ""])
    if not result["failures"]:
        lines.append("None.")
    for failure in result["failures"]:
        lines.extend([f"### Case {failure['case']}", "", "```json",
                      json.dumps(failure, ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DIRECTORY / "dataset.jsonl")
    parser.add_argument("--extractor", choices=("llm", "regex"), default="llm")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.output is None:
        args.output = DIRECTORY / ("results-baseline.md" if args.extractor == "regex" else "results.md")
    if args.dataset.resolve() == args.output.resolve():
        print("Output must not overwrite the dataset.", file=sys.stderr)
        return 1
    try:
        rows = load_dataset(args.dataset)
        if args.extractor == "regex":
            result = evaluate(rows, extract_baseline)
            provider, model = "local", "regex-baseline"
        else:
            settings = load_settings()
            result = evaluate(rows, lambda message: extract_order(message, settings))
            provider, model = settings.provider, settings.model
        report = render_report(result, provider, model, args.dataset)
        args.output.write_text(report, encoding="utf-8")
    except ValidationError:
        print("Configuration error: set PROVIDER, MODEL, and API_KEY in .env.", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"Evaluation failed: {error}", file=sys.stderr)
        return 1
    print(f"Evaluated {result['total']} messages; overall accuracy {result['overall_accuracy']:.2%}; "
          f"extraction errors {result['errors']}. Report: {args.output}")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
