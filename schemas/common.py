"""Shared Pydantic helpers used across the schema layer.

This module keeps the schema layer lightweight and compatible with the current
codebase while we gradually replace loose dictionaries with typed models.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict


class SchemaModel(BaseModel):
    """Base model with permissive defaults for gradual migration.

    The current codebase still contains mixed and partially-migrated objects.
    Allowing extra fields keeps the schema layer helpful without forcing every
    caller to move at once.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @classmethod
    def from_data(cls, value: Any):
        """Create the model from an existing model instance or a mapping."""
        if isinstance(value, cls):
            return value
        if value is None:
            return cls()
        if isinstance(value, Mapping):
            return cls.model_validate(dict(value))
        raise TypeError(f"Cannot build {cls.__name__} from {type(value).__name__}")

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe dictionary for compatibility with legacy callers."""
        return self.model_dump(mode="json")


SchemaT = TypeVar("SchemaT", bound=SchemaModel)


def ensure_schema(value: Any, schema_cls: Type[SchemaT]) -> SchemaT:
    """Coerce a mapping or existing model into the requested schema type."""
    return schema_cls.from_data(value)


def ensure_schema_list(values: Optional[Iterable[Any]], schema_cls: Type[SchemaT]) -> List[SchemaT]:
    """Coerce an iterable of mappings/models into typed schema instances."""
    if not values:
        return []
    return [ensure_schema(value, schema_cls) for value in values]
