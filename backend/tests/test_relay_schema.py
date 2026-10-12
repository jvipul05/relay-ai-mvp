import pytest
from fastapi import HTTPException
from jsonschema import Draft202012Validator

from app.api.relay_studio import _default_schema, _get_schema


@pytest.mark.parametrize("destination", ["auto", "jira", "confluence", "slack"])
def test_builtin_relay_schemas_are_valid_json_schemas(destination):
    schema = _default_schema(destination)
    Draft202012Validator.check_schema(schema)
    assert schema["type"] == "object"
    assert schema.get("required")


def test_custom_schema_rejects_unsupported_keywords():
    schema = '{"type":"object","properties":{"value":{"type":"string","$ref":"#"}}}'
    with pytest.raises(HTTPException) as error:
        _get_schema("auto", schema)
    assert error.value.status_code == 422
