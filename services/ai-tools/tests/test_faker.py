"""스키마 가짜 값: 다양한 스키마(Pydantic 생성 포함)에서 항상 스키마를 통과해야 한다."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated, Literal

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, Field

from winmate_ai_tools.faker import fake, ko_label


class Color(str, Enum):
    red = "red"
    blue = "blue"


class Contact(BaseModel):
    name: str
    email: str | None = Field(default=None, json_schema_extra={"format": "email"})
    phone: str = Field(pattern=r"^\d{2,3}-\d{3,4}-\d{4}$", default="02-123-4567")


class Item(BaseModel):
    title: str = Field(min_length=3, max_length=40)
    qty: int = Field(ge=1, le=10)
    price: float = Field(gt=0, lt=1_000_000)
    color: Color = Color.red
    tags: list[str] = Field(default_factory=list, max_length=3)


class Node(BaseModel):
    label: str
    children: list[Node] = Field(default_factory=list)


class Cat(BaseModel):
    kind: Literal["cat"]
    meow: int


class Dog(BaseModel):
    kind: Literal["dog"]
    bark: bool


class Form(BaseModel):
    customer: str = Field(description="고객사 이름")
    industry: Literal["retail", "hotel", "office"]
    due: date
    items: list[Item] = Field(min_length=1, max_length=5)
    contacts: list[Contact] = Field(default_factory=list)
    notes: str | None = None
    score: Annotated[float, Field(ge=0, le=1, multiple_of=0.25)] = 0.5
    tree: Node | None = None
    pet: Annotated[Cat | Dog, Field(discriminator="kind")]
    extra: dict[str, int] = Field(default_factory=dict)
    pair: tuple[int, str]


SCHEMAS: list[dict] = [
    Form.model_json_schema(),
    Item.model_json_schema(),
    Node.model_json_schema(),
    {"type": "object", "properties": {"a": {"type": "string", "minLength": 50}}, "required": ["a"]},
    {"type": "object", "properties": {"a": {"type": "string", "maxLength": 2}}, "required": ["a"]},
    {"type": "array", "items": {"type": "integer", "minimum": 5, "exclusiveMaximum": 7}, "minItems": 3, "uniqueItems": False},
    {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4, "uniqueItems": True},
    {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 100}, "minItems": 5, "uniqueItems": True},
    {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1},
    {"type": "integer", "multipleOf": 7, "minimum": 10},
    {"type": "integer", "maximum": -3},
    {"type": ["string", "null"], "format": "date-time"},
    {"type": "string", "format": "uri"},
    {"type": "string", "format": "uuid"},
    {"type": "string", "enum": ["a", "b"]},
    {"const": {"x": 1}},
    {"type": "boolean"},
    {"type": "null"},
    {"anyOf": [{"type": "null"}, {"type": "object", "properties": {"q": {"type": "integer"}}, "required": ["q"]}]},
    {"oneOf": [{"type": "string", "maxLength": 3}, {"type": "integer"}]},
    {"allOf": [{"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]},
               {"properties": {"b": {"type": "integer", "minimum": 3}}, "required": ["b"]}]},
    {"type": "object", "minProperties": 2, "additionalProperties": {"type": "number"}},
    {"type": "object", "properties": {"a": {"type": "string"}}, "maxProperties": 1, "required": ["a"]},
    {"type": "array", "prefixItems": [{"type": "string"}, {"type": "number"}], "items": False},
    {"$defs": {"x": {"type": "string", "pattern": "^[A-Z]{2}$"}}, "type": "object",
     "properties": {"code": {"$ref": "#/$defs/x"}}, "required": ["code"]},
    {"definitions": {"p": {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}},
     "type": "array", "items": {"$ref": "#/definitions/p"}, "minItems": 1},
    {"type": "object", "properties": {"competitors": {"type": "array", "items": {"type": "object", "properties": {
        "name": {"type": "string"}, "strengths": {"type": "array", "items": {"type": "string"}}}, "required": ["name", "strengths"]}}}},
    {},
    {"type": "object"},
]


@pytest.mark.parametrize("schema", SCHEMAS, ids=[str(i) for i in range(len(SCHEMAS))])
def test_faker_valid(schema):
    value = fake(schema)
    v = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(value)]
    assert not errors, (value, errors)


def test_faker_deterministic_and_korean():
    s = Form.model_json_schema()
    a, b = fake(s), fake(s)
    assert a == b
    assert a["customer"] == "[mock] 고객사 이름"   # 한국어 description
    assert len(a["items"]) >= 1 and a["items"][0]["title"].startswith("[mock]")
    Form.model_validate(a)   # 원래 Pydantic 모델로도 통과


def test_array_strings_numbered():
    v = fake({"type": "object", "properties": {"competitors": {"type": "array", "items": {"type": "string"}}}})
    assert v == {"competitors": ["[mock] 경쟁사", "[mock] 경쟁사 2"]}


def test_ko_label():
    assert ko_label("customer_name") == "고객사 이름"
    assert ko_label("productModel") == "제품 모델"
    assert ko_label("unknownThing") == "unknown Thing"
    assert ko_label("x", {"title": "요구사항 목록"}) == "요구사항 목록"
