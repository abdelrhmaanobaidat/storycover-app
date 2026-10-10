from functools import lru_cache

from google import genai
from google.genai import types

from .config import settings


class CoverGenerationError(RuntimeError):
    """Gemini returned no usable image."""


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    if not settings.gemini_api_key:
        raise CoverGenerationError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=settings.gemini_api_key)


def _prompt(title: str) -> str:
    return (
        "Create a children's story-book cover illustration based on the attached photo. "
        f'Title the cover "{title}" in a large, playful hand-lettered font near the top. '
        "Warm, whimsical, painterly style. Return an image."
    )


def generate_cover(image_bytes: bytes, mime_type: str, title: str) -> tuple[bytes, str]:
    """Send the photo + title to Gemini and return the generated cover (bytes, mime)."""
    response = _client().models.generate_content(
        model=settings.gemini_model,
        contents=[
            _prompt(title),
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )

    for candidate in response.candidates or []:
        for part in candidate.content.parts or []:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return inline.data, inline.mime_type or "image/png"

    raise CoverGenerationError("Gemini response contained no image")
