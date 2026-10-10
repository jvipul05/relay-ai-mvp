"""Small, deterministic text chunker. Keeps implementation dependency-light."""
import re


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    cleaned = re.sub(r"\r\n?", "\n", (text or "")).strip()
    cleaned = re.sub(r"[\t ]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if not cleaned:
        return []
    if chunk_size < 100 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be >= 100 and overlap must be between 0 and chunk_size")

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        if end < len(cleaned):
            # Prefer breaking on a paragraph or sentence near the end of the window.
            floor = start + int(chunk_size * 0.65)
            boundary = max(cleaned.rfind("\n", floor, end), cleaned.rfind(". ", floor, end), cleaned.rfind(" ", floor, end))
            if boundary > start:
                end = boundary + (1 if cleaned[boundary:boundary + 1] == "\n" else 2 if cleaned[boundary:boundary + 2] == ". " else 0)
        part = cleaned[start:end].strip()
        if part:
            chunks.append(part)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks
