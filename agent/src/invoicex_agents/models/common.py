"""Shared strict models and source-evidence contracts."""

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    """Convert a snake_case field name to lower camelCase."""

    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class StrictModel(BaseModel):
    """Base model that rejects unspecified Gemini output fields."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class SourceEvidence(StrictModel):
    """A short locator that ties a result to an uploaded document."""

    evidence_id: str = Field(min_length=1, max_length=100)
    document_id: str = Field(min_length=1, max_length=100)
    page: int = Field(ge=1)
    field: str = Field(min_length=1, max_length=100)
    quote: str = Field(min_length=1, max_length=500)
