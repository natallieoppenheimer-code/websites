"""
Generate short voice notes via ElevenLabs TTS for SMS realism.
Uses a female voice (Rachel) so replies sound like Natalie.
"""
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ElevenLabs female voice: Rachel — natural, clear (fits Natalie persona)
# https://elevenlabs.io/voice-library/adult-female-voices
ELEVENLABS_VOICE_ID_FEMALE = "21m00Tcm4TlvDq8ikWAM"
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"
ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"

# Keep voice notes short for "a little" realism (chars)
VOICE_NOTE_MAX_CHARS = 200


def _shorten_for_voice_note(text: str) -> str:
    """Trim text to a short clip suitable for a voice note."""
    text = (text or "").strip()
    if len(text) <= VOICE_NOTE_MAX_CHARS:
        return text
    # Cut at last space before limit to avoid mid-word
    truncated = text[: VOICE_NOTE_MAX_CHARS + 1]
    last_space = truncated.rfind(" ")
    if last_space > VOICE_NOTE_MAX_CHARS // 2:
        return truncated[:last_space].strip()
    return truncated.strip()


def generate_voice_note(
    text: str,
    api_key: str,
    voice_id: str = ELEVENLABS_VOICE_ID_FEMALE,
    model_id: str = ELEVENLABS_MODEL_ID,
    output_format: str = ELEVENLABS_OUTPUT_FORMAT,
    storage_dir: Optional[Path] = None,
) -> Tuple[Optional[str], Optional[Path]]:
    """
    Generate a short voice note (female voice) and save to disk.
    Returns (file_id, path) or (None, None) on failure.
    file_id is the basename without extension (e.g. abc123) for the URL.
    """
    if not api_key or not text.strip():
        return (None, None)
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        logger.warning("elevenlabs package not installed; skipping voice note")
        return (None, None)

    short_text = _shorten_for_voice_note(text)
    if not short_text:
        return (None, None)

    try:
        client = ElevenLabs(api_key=api_key)
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=short_text,
            model_id=model_id,
            output_format=output_format,
        )
    except Exception as e:
        logger.warning("ElevenLabs TTS failed: %s", e)
        return (None, None)

    if not storage_dir:
        storage_dir = Path(__file__).resolve().parent.parent.parent / "voice_notes"
    storage_dir = Path(storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    raw = b""
    if isinstance(audio, bytes):
        raw = audio
    else:
        for chunk in audio:
            if chunk:
                raw += chunk if isinstance(chunk, bytes) else bytes(chunk)

    if not raw:
        return (None, None)

    file_id = hashlib.sha256(raw).hexdigest()[:16]
    out_path = storage_dir / f"{file_id}.mp3"
    out_path.write_bytes(raw)
    logger.info("Voice note saved: %s (%d bytes)", out_path.name, len(raw))
    return (file_id, out_path)
