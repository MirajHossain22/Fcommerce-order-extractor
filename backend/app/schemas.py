"""Validated order fields shared by extraction and later API phases."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


Text64 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64, strict=True)]
Text80 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80, strict=True)]
Text100 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, strict=True)]
Text150 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150, strict=True)]
Text200 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200, strict=True)]
Text300 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300, strict=True)]
Text2000 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000, strict=True)]
Message = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000, strict=True)]
WarningText = Annotated[str, StringConstraints(max_length=500, strict=True)]


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Message


class BatchExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[Message] = Field(min_length=1, max_length=50)


class Order(BaseModel):
    """Missing information stays null; warnings describe rejected values."""

    model_config = ConfigDict(extra="forbid", strict=True)

    is_order: bool
    customer_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, pattern=r"^01[3-9][0-9]{8}$")
    address: str | None = Field(default=None, max_length=2000)
    product: str | None = Field(default=None, max_length=500)
    quantity: int | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=2000)
    warnings: list[WarningText] = Field(default_factory=list, max_length=50)
