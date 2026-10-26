"""Validated order fields shared by extraction and later API phases."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


Message = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, strict=True)]


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Message


class BatchExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[Message] = Field(min_length=1)


class Order(BaseModel):
    """Missing information stays null; warnings describe rejected values."""

    model_config = ConfigDict(extra="forbid", strict=True)

    is_order: bool
    customer_name: str | None = None
    phone: str | None = Field(default=None, pattern=r"^01[3-9][0-9]{8}$")
    address: str | None = None
    product: str | None = None
    quantity: int | None = Field(default=None, gt=0)
    notes: str | None = None
    warnings: list[str] = Field(default_factory=list)
