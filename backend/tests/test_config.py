from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import load_settings


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("PROVIDER", "MODEL", "API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)


def test_load_dotenv(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("PROVIDER=test-provider\nMODEL=test-model\nAPI_KEY=FAKE_TEST_KEY\n", encoding="utf-8")
    settings = load_settings(env_file)
    assert settings.provider == "test-provider"
    assert settings.model == "test-model"
    assert settings.api_key.get_secret_value() == "FAKE_TEST_KEY"
    assert "FAKE_TEST_KEY" not in repr(settings)


def test_environment_overrides_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("PROVIDER=file-provider\nMODEL=file-model\nAPI_KEY=FAKE_FILE_KEY\n", encoding="utf-8")
    monkeypatch.setenv("PROVIDER", " env-provider ")
    monkeypatch.setenv("MODEL", "env-model")
    monkeypatch.setenv("API_KEY", "FAKE_ENV_KEY")
    settings = load_settings(env_file)
    assert settings.provider == "env-provider"
    assert settings.model == "env-model"
    assert settings.api_key.get_secret_value() == "FAKE_ENV_KEY"


def test_missing_configuration_fails(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_settings(tmp_path / "missing.env")


@pytest.mark.parametrize("blank_key", ["PROVIDER", "MODEL", "API_KEY"])
def test_blank_configuration_fails(blank_key: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {"PROVIDER": "test", "MODEL": "test", "API_KEY": "FAKE_TEST_KEY"}.items():
        monkeypatch.setenv(key, " " if key == blank_key else value)
    with pytest.raises(ValidationError):
        load_settings(tmp_path / "missing.env")
