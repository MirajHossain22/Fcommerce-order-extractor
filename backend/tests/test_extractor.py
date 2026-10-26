import json
from io import StringIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.extractor import ExtractionError, call_llm, extract_order, main, validate_extraction


def response(**fields: object) -> str:
    data = dict.fromkeys(("customer_name", "phone", "address", "product", "quantity", "notes"))
    return json.dumps({**data, "is_order": True, **fields}, ensure_ascii=False)


def test_missing_fields_are_null() -> None:
    order = validate_extraction(response(), "ei product ta lagbe")
    assert order.is_order
    for field in ("customer_name", "phone", "address", "product", "quantity", "notes"):
        assert getattr(order, field) is None


def test_preserves_source_and_normalizes_phone() -> None:
    order = validate_extraction(
        response(customer_name="TEST_CUSTOMER", phone="+৮৮০ ১৭০০-০০০০০০", product="পরীক্ষা পণ্য", quantity=2),
        "TEST_CUSTOMER: পরীক্ষা পণ্য ২টা চাই, ফোন +৮৮০ ১৭০০-০০০০০০",
    )
    assert order.customer_name == "TEST_CUSTOMER"
    assert order.product == "পরীক্ষা পণ্য"
    assert order.phone == "01700000000"
    assert order.quantity == 2
    assert order.warnings == []


def test_invalid_source_phone_is_flagged() -> None:
    order = validate_extraction(response(phone="00000"), "order chai, phone 00000")
    assert order.phone is None
    assert "Invalid phone" in order.warnings[0]


@pytest.mark.parametrize("field", ["customer_name", "phone", "address", "product", "notes"])
def test_invented_text_is_discarded(field: str) -> None:
    order = validate_extraction(response(**{field: "INVENTED_VALUE"}), "order chai")
    assert getattr(order, field) is None
    assert order.warnings == [f"Unsupported {field}: value not present in message."]


def test_non_order_has_no_order_fields() -> None:
    order = validate_extraction(response(is_order=False, product="TEST_PRODUCT", quantity=2), "TEST_PRODUCT 2 ta ache?")
    assert not order.is_order
    assert order.product is None
    assert order.quantity is None


@pytest.mark.parametrize("raw", ["not json", "[]", "{}", response(quantity=0), response(quantity=True), response(quantity="২"), response(extra="unknown")])
def test_rejects_invalid_output(raw: str) -> None:
    with pytest.raises(ValidationError):
        validate_extraction(raw, "test message")


@pytest.fixture
def settings() -> Settings:
    return Settings(provider="gemini", model="test-model", api_key="FAKE_TEST_KEY")


@pytest.mark.parametrize("bad_output", ["not JSON", response(quantity=-1), response(quantity="2"), "{}"])
def test_retries_invalid_output_once(settings: Settings, bad_output: str) -> None:
    with patch("app.extractor.call_llm", side_effect=[bad_output, response(quantity=2)]) as llm:
        assert extract_order("2 ta chai", settings).quantity == 2
    assert llm.call_count == 2
    assert llm.call_args.kwargs == {"retry": True}


def test_stops_after_two_invalid_outputs(settings: Settings) -> None:
    with patch("app.extractor.call_llm", return_value="bad") as llm:
        with pytest.raises(ExtractionError, match="two attempts"):
            extract_order("order chai", settings)
    assert llm.call_count == 2


def test_provider_failure_is_not_retried(settings: Settings) -> None:
    with patch("app.extractor.call_llm", side_effect=ExtractionError("network failure")) as llm:
        with pytest.raises(ExtractionError, match="network"):
            extract_order("order chai", settings)
    llm.assert_called_once()


def test_blank_message_never_calls_provider(settings: Settings) -> None:
    with patch("app.extractor.call_llm") as llm:
        with pytest.raises(ExtractionError, match="blank"):
            extract_order(" \n", settings)
    llm.assert_not_called()


def test_loads_settings_when_omitted(settings: Settings) -> None:
    with patch("app.extractor.load_settings", return_value=settings) as config:
        with patch("app.extractor.call_llm", return_value=response()) as llm:
            extract_order("order chai")
    config.assert_called_once_with()
    assert llm.call_args.args[1] is settings


def api_response(text: str) -> dict[str, object]:
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]}


def mock_http(payload: object) -> MagicMock:
    http = MagicMock()
    http.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
    return http


def test_gemini_request_contract(settings: Settings) -> None:
    output = response()
    with patch("app.extractor.urlopen", return_value=mock_http(api_response(output))) as http:
        assert call_llm("পরীক্ষা অর্ডার চাই", settings, retry=True) == output
    request = http.call_args.args[0]
    assert request.full_url == "https://generativelanguage.googleapis.com/v1beta/models/test-model:generateContent"
    assert request.get_method() == "POST"
    assert request.get_header("X-goog-api-key") == "FAKE_TEST_KEY"
    assert "FAKE_TEST_KEY" not in request.full_url
    assert http.call_args.kwargs["timeout"] == 60
    body = json.loads(request.data)
    assert body["contents"] == [{"role": "user", "parts": [{"text": "পরীক্ষা অর্ডার চাই"}]}]
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    schema = body["generationConfig"]["responseJsonSchema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(json.loads(output))
    prompt = body["systemInstruction"]["parts"][0]["text"]
    assert "Never guess or invent names, phone numbers, addresses" in prompt
    assert "previous output failed validation" in prompt


def test_unsupported_provider_fails_without_network(settings: Settings) -> None:
    settings.provider = "unsupported"
    with patch("app.extractor.urlopen") as http:
        with pytest.raises(ExtractionError, match="Unsupported PROVIDER"):
            call_llm("order chai", settings)
    http.assert_not_called()


@pytest.mark.parametrize("error", [URLError("FAKE_TEST_KEY"), TimeoutError("FAKE_TEST_KEY"), HTTPError("https://example.invalid", 401, "FAKE_TEST_KEY", {}, None)])
def test_network_errors_do_not_expose_secrets(settings: Settings, error: Exception) -> None:
    with patch("app.extractor.urlopen", side_effect=error):
        with pytest.raises(ExtractionError) as caught:
            call_llm("order chai", settings)
    assert "FAKE_TEST_KEY" not in str(caught.value)


@pytest.mark.parametrize("payload", [None, {}, {"candidates": []}, {"candidates": [{"finishReason": "SAFETY"}]}, {"candidates": [{"finishReason": "MAX_TOKENS"}]}, api_response("")])
def test_rejects_unusable_api_responses(settings: Settings, payload: object) -> None:
    with patch("app.extractor.urlopen", return_value=mock_http(payload)):
        with pytest.raises(ExtractionError):
            call_llm("order chai", settings)


def test_ignores_thought_parts(settings: Settings) -> None:
    payload = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
        {"text": "internal thoughts", "thought": True}, {"text": response()},
    ]}}]}
    with patch("app.extractor.urlopen", return_value=mock_http(payload)):
        assert call_llm("order chai", settings) == response()


def test_invalid_api_json_is_reported(settings: Settings) -> None:
    http = MagicMock()
    http.__enter__.return_value.read.return_value = b"not json"
    with patch("app.extractor.urlopen", return_value=http):
        with pytest.raises(ExtractionError, match="invalid API response"):
            call_llm("order chai", settings)


def test_full_extraction_retries_over_http(settings: Settings) -> None:
    responses = [mock_http(api_response("bad json")), mock_http(api_response(response(phone="00000")))]
    with patch("app.extractor.urlopen", side_effect=responses) as http:
        order = extract_order("order chai, phone 00000", settings)
    assert http.call_count == 2
    assert order.phone is None
    assert "Invalid phone" in order.warnings[0]


# Ten synthetic orders and two non-orders. Mocked outputs test plumbing,
# normalization, and null preservation, NOT the model's semantic accuracy.
@pytest.mark.parametrize(("message", "fields"), [
    ("পরীক্ষা পণ্য ২টা চাই", {"product": "পরীক্ষা পণ্য", "quantity": 2}),
    ("bhai TEST_PRODUCT 3 ta lagbe", {"product": "TEST_PRODUCT", "quantity": 3}),
    ("TEST_PRODUCT ২টা order, name TEST_CUSTOMER", {"product": "TEST_PRODUCT", "quantity": 2, "customer_name": "TEST_CUSTOMER"}),
    ("Please order TEST_PRODUCT", {"product": "TEST_PRODUCT"}),
    ("অর্ডার চাই, নাম TEST_CUSTOMER", {"customer_name": "TEST_CUSTOMER"}),
    ("order chai, address TEST_ADDRESS_000", {"address": "TEST_ADDRESS_000"}),
    ("TEST_PRODUCT chai, phone ০১৭০০-০০০০০০", {"product": "TEST_PRODUCT", "phone": "০১৭০০-০০০০০০"}),
    ("order chai, phone +880 1700 000000", {"phone": "+880 1700 000000"}),
    ("TEST_PRODUCT lagbe, phone 00000", {"product": "TEST_PRODUCT", "phone": "00000"}),
    ("একটা পরীক্ষা পণ্য চাই, gift wrap", {"product": "পরীক্ষা পণ্য", "quantity": 1, "notes": "gift wrap"}),
    ("hello, কেমন আছেন?", {"is_order": False}),
    ("TEST_PRODUCT er price koto?", {"is_order": False}),
])
def test_synthetic_message_plumbing(settings: Settings, message: str, fields: dict[str, object]) -> None:
    with patch("app.extractor.call_llm", return_value=response(**fields)) as llm:
        order = extract_order(message, settings)
    llm.assert_called_once_with(message, settings)
    assert order.is_order == fields.get("is_order", True)
    for field in ("customer_name", "address", "product", "quantity", "notes"):
        assert getattr(order, field) == fields.get(field)
    if fields.get("phone") == "00000":
        assert order.phone is None
        assert len(order.warnings) == 1
    elif fields.get("phone"):
        assert order.phone == "01700000000"
        assert not order.warnings
    else:
        assert order.phone is None
        assert not order.warnings


def test_cli_argument_prints_json(settings: Settings, capsys: pytest.CaptureFixture[str]) -> None:
    with patch("app.extractor.load_settings", return_value=settings):
        with patch("app.extractor.call_llm", return_value=response(product="পরীক্ষা পণ্য")):
            assert main(["পরীক্ষা পণ্য চাই"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["product"] == "পরীক্ষা পণ্য"
    assert json.loads(captured.out)["quantity"] is None
    assert captured.err == ""


def test_cli_reads_stdin(settings: Settings, capsys: pytest.CaptureFixture[str]) -> None:
    with patch("app.extractor.load_settings", return_value=settings):
        with patch("app.extractor.sys.stdin", StringIO("hello")):
            with patch("app.extractor.call_llm", return_value=response(is_order=False)):
                assert main([]) == 0
    assert json.loads(capsys.readouterr().out)["is_order"] is False


def test_cli_error_goes_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([" "]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Message must not be blank" in captured.err


def test_cli_hides_configuration_values(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ValidationError) as invalid:
        Settings(provider="", model="test", api_key="FAKE_TEST_KEY")
    with patch("app.extractor.load_settings", side_effect=invalid.value):
        assert main(["order chai"]) == 1
    captured = capsys.readouterr()
    assert "Configuration error" in captured.err
    assert "FAKE_TEST_KEY" not in captured.err
