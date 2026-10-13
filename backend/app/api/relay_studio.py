"""Multilingual Gemini Relay Studio: multimodal input -> structured preview -> human approval."""
import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from jsonschema import Draft202012Validator, ValidationError as JsonSchemaValidationError
from sqlalchemy.orm import Session
from google.genai import types
from starlette.concurrency import run_in_threadpool

from app.core.database import get_db
from app.services.project_service import load_project_payload
from ai_agent import normalize_language, relay_structured_output

router = APIRouter(prefix="/api/projects/{project_id}/relay", tags=["relay-studio"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MEDIA_TYPES = {
    "image/png", "image/jpeg", "image/webp", "image/gif",
    "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/mp4",
    "audio/m4a", "audio/x-m4a", "audio/aac", "audio/ogg", "audio/flac",
}
SUPPORTED_SCHEMA_TYPES = {"object", "array", "string", "integer", "number", "boolean"}
SCHEMA_KEYWORDS = {
    "type", "properties", "required", "items", "enum", "description", "format",
    "minimum", "maximum", "minItems", "maxItems", "additionalProperties", "title",
}


def _action_items_schema():
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short actionable item"},
                "owner": {"type": "string", "description": "Owner, or Not specified"},
                "due_date": {"type": "string", "description": "ISO date or Not specified"},
                "priority": {"type": "string", "enum": ["Highest", "High", "Medium", "Low", "Not specified"]},
            },
            "required": ["title", "owner", "due_date", "priority"],
            "additionalProperties": False,
        },
    }


def _default_schema(destination: str) -> dict:
    if destination == "jira":
        return {
            "type": "object",
            "properties": {
                "issue_type": {"type": "string", "enum": ["Bug", "Task", "Story", "Incident"]},
                "summary": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["Highest", "High", "Medium", "Low", "Lowest"]},
                "labels": {"type": "array", "items": {"type": "string"}},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                "action_items": _action_items_schema(),
                "assumptions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["issue_type", "summary", "description", "priority", "labels", "acceptance_criteria", "action_items", "assumptions"],
            "additionalProperties": False,
        }
    if destination == "confluence":
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "sections": {
                    "type": "array",
                    "items": {"type": "object", "properties": {
                        "heading": {"type": "string"}, "body": {"type": "string"},
                    }, "required": ["heading", "body"], "additionalProperties": False},
                },
                "decisions": {"type": "array", "items": {"type": "string"}},
                "action_items": _action_items_schema(),
                "assumptions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "summary", "sections", "decisions", "action_items", "assumptions"],
            "additionalProperties": False,
        }
    if destination == "slack":
        return {
            "type": "object",
            "properties": {
                "channel_message": {"type": "string"},
                "key_points": {"type": "array", "items": {"type": "string"}},
                "action_items": _action_items_schema(),
                "open_questions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["channel_message", "key_points", "action_items", "open_questions"],
            "additionalProperties": False,
        }
    return {
        "type": "object",
        "properties": {
            "detected_type": {"type": "string", "enum": ["code", "log", "meeting_notes", "project_update", "incident", "support_request", "other"]},
            "recommended_destination": {"type": "string", "enum": ["jira", "confluence", "slack", "manual_review"]},
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "structured_payload": {"type": "object", "properties": {}, "additionalProperties": True},
            "action_items": _action_items_schema(),
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["detected_type", "recommended_destination", "title", "summary", "structured_payload", "action_items", "assumptions", "open_questions"],
        "additionalProperties": False,
    }


def _validate_schema_tree(node: dict, depth: int = 0) -> None:
    if depth > 4:
        raise HTTPException(status_code=422, detail="Custom schema is too deeply nested (maximum depth: 4).")
    if not isinstance(node, dict):
        raise HTTPException(status_code=422, detail="Each custom schema node must be a JSON object.")
    unknown = set(node) - SCHEMA_KEYWORDS
    if unknown:
        raise HTTPException(status_code=422, detail="Unsupported JSON Schema keywords: " + ", ".join(sorted(unknown)))
    node_type = node.get("type")
    if node_type not in SUPPORTED_SCHEMA_TYPES:
        raise HTTPException(status_code=422, detail="Every custom schema node must specify a supported type.")
    if "enum" in node and (not isinstance(node["enum"], list) or not node["enum"] or len(node["enum"]) > 30):
        raise HTTPException(status_code=422, detail="Schema enum values must be a non-empty list of at most 30 values.")
    if node_type == "object":
        properties = node.get("properties", {})
        required = node.get("required", [])
        if not isinstance(properties, dict) or len(properties) > 12:
            raise HTTPException(status_code=422, detail="Each object schema may contain at most 12 properties.")
        if not isinstance(required, list) or any(key not in properties for key in required):
            raise HTTPException(status_code=422, detail="Schema required fields must be listed in properties.")
        if "additionalProperties" in node and not isinstance(node["additionalProperties"], bool):
            raise HTTPException(status_code=422, detail="Use a boolean for additionalProperties.")
        for child in properties.values():
            _validate_schema_tree(child, depth + 1)
    elif node_type == "array":
        if "items" not in node:
            raise HTTPException(status_code=422, detail="Array schema nodes must define items.")
        _validate_schema_tree(node["items"], depth + 1)


def _get_schema(destination: str, schema_json: str | None) -> dict:
    if not schema_json or not schema_json.strip():
        return _default_schema(destination)
    if len(schema_json) > 8000:
        raise HTTPException(status_code=413, detail="Custom schema must be 8 KB or smaller.")
    try:
        schema = json.loads(schema_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Custom schema is not valid JSON.") from exc
    if not isinstance(schema, dict) or schema.get("type") != "object" or "properties" not in schema:
        raise HTTPException(status_code=422, detail="Custom schema must be an object schema with properties.")
    _validate_schema_tree(schema)
    try:
        Draft202012Validator.check_schema(schema)
    except JsonSchemaValidationError as exc:
        raise HTTPException(status_code=422, detail="Custom schema is invalid: " + str(exc.message)[:250]) from exc
    return schema


@router.post("/preview")
async def preview_relay_payload(
    project_id: str,
    input_text: str = Form(default="", max_length=12000),
    destination: Literal["auto", "jira", "confluence", "slack"] = Form(default="auto"),
    language: str = Form(default="English", max_length=40),
    schema_text: str = Form(default="", alias="schema_json"),
    use_google_search: bool = Form(default=False),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    project = load_project_payload(db, project_id)
    text = input_text.strip()
    media_part = None
    attachment = None
    if file is not None and file.filename:
        mime_type = (file.content_type or "").lower().split(";")[0].strip()
        if mime_type not in ALLOWED_MEDIA_TYPES:
            raise HTTPException(status_code=415, detail="Upload one supported image (PNG/JPEG/WebP/GIF) or audio file (WAV/MP3/M4A/OGG/FLAC/AAC).")
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Attachment is too large. Maximum file size is 10 MB.")
        if not data:
            raise HTTPException(status_code=422, detail="The uploaded attachment is empty.")
        media_part = types.Part.from_bytes(data=data, mime_type=mime_type)
        attachment = {
            "filename": file.filename.split("/")[-1].split("\\")[-1][:255],
            "mime_type": mime_type,
            "size_bytes": len(data),
        }
    if not text and media_part is None:
        raise HTTPException(status_code=422, detail="Enter text or attach an image/audio file before generating a preview.")

    try:
        selected_language = normalize_language(language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    schema = _get_schema(destination, schema_text)
    schema_for_model = dict(schema)
    schema_for_model["_relay_destination"] = destination
    project_context = {
        "id": project.get("id"), "name": project.get("name"), "status": project.get("status"),
        "planned_release": project.get("planned_release"),
        "tasks": project.get("tasks", [])[:15],
    }
    try:
        generated = await run_in_threadpool(
            relay_structured_output,
            {
                "input_text": text,
                "attachment_description": (
                    f"{attachment['filename']} ({attachment['mime_type']}, {attachment['size_bytes']} bytes)"
                    if attachment else "No attachment"
                ),
                "media_part": media_part,
                "project_context": project_context,
            },
            schema_for_model,
            language=selected_language,
            use_google_search=use_google_search,
            search_query=text,
        )
        schema_validator = Draft202012Validator(schema)
        schema_validator.validate(generated["output"])
    except JsonSchemaValidationError as exc:
        print(f"Relay output failed schema validation: {exc.message}")
        raise HTTPException(status_code=502, detail="Gemini output did not pass JSON Schema validation. Try again or simplify the custom schema.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Relay preview failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"Relay preview failed ({type(exc).__name__}). Check backend logs.") from exc

    output = generated["output"]
    resolved_destination = destination
    if destination == "auto":
        recommended = output.get("recommended_destination", "manual_review")
        resolved_destination = recommended if recommended in {"jira", "confluence", "slack"} else "manual_review"

    return {
        "project_id": project_id,
        "destination_requested": destination,
        "resolved_destination": resolved_destination,
        "language": selected_language,
        "model": generated["model"],
        "original_text": text,
        "attachment": attachment,
        "schema": schema,
        "output": output,
        "grounding": generated["grounding"],
        "external_write_performed": False,
        "pipeline": [
            {"id": "ingest", "label": "Input received", "status": "complete"},
            {"id": "classify", "label": "Gemini routing and reasoning", "status": "complete"},
            {"id": "structure", "label": "Structured output validated", "status": "complete"},
            {"id": "review", "label": "Ready for human review", "status": "current"},
        ],
        "notice": "Preview only. No Jira, Confluence, Slack, or other external system was modified.",
    }
