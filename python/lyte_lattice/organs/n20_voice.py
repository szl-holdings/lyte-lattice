"""N20 Voice — LiveKit / Cartesia / Deepgram cited job. Not those products.

Cite the leader. Take the job. Do not rehost.
STT/TTS plan only. No audio bytes. No room.
"""
from __future__ import annotations

from typing import Any, Mapping

from lyte_lattice.organ import seal, text

DEFAULT_TEXT = "Claim 9001 is open. Reserve twelve thousand."
VOWELS = "aeiou"
NOTE = "No audio synthesized. Cartesia/Deepgram not called."
ROOM = {"livekit": False, "note": "Not a LiveKit room"}


def _words(s: str) -> list[str]:
    return [w for w in (s or "").split() if w]


def _viseme_shape(word: str) -> str:
    for ch in word:
        cl = ch.lower()
        if cl in VOWELS:
            return cl.upper()
    return "rest"


def _viseme_stream(text_value: str) -> list[str]:
    stream: list[str] = []
    for ch in text_value:
        cl = ch.lower()
        if cl in VOWELS:
            stream.append(cl.upper())
        elif cl.isalpha():
            stream.append("rest")
    return stream


def _phoneme_silhouette(words: list[str]) -> list[str]:
    out: list[str] = []
    for w in words:
        core = w.strip(".,;:!?\"'()[]{}")
        token = core or w
        if not token:
            continue
        if len(token) == 1:
            out.append(token.lower())
        else:
            out.append((token[0] + token[-1]).lower())
    return out


def _plan(text_value: str, voice: str) -> dict[str, Any]:
    words = _words(text_value)
    duration_s = round(len(words) * 0.38 + 0.4, 4)
    visemes = []
    t = 0.0
    for w in words:
        visemes.append({"t_s": round(t, 3), "word": w, "shape": _viseme_shape(w)})
        t += 0.38
    return {
        "text": text_value,
        "voice": voice or "hologram-unvoiced",
        "words": words,
        "word_count": len(words),
        "duration_s": duration_s,
        "duration_honesty": "REPORTED",
        "duration_model": "words*0.38+0.4",
        "visemes": visemes,
        "viseme_stream": _viseme_stream(text_value),
        "phonemes": _phoneme_silhouette(words),
        "room": dict(ROOM),
        "audio_bytes": None,
        "note": NOTE,
    }


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    direction = text(payload, "direction", default="tts").lower() or "tts"
    if direction not in {"tts", "stt"}:
        direction = "tts"
    voice = text(payload, "voice")
    supplied = text(payload, "text")

    if direction == "stt":
        if not supplied:
            plan = _plan("", voice)
            plan.update(
                {
                    "direction": "stt",
                    "transcript": "",
                    "confidence": None,
                    "confidence_honesty": "UNAVAILABLE",
                    "error": "no audio in this hologram",
                }
            )
            return seal(cell="N20", status="warn", payload=payload, output=plan)
        plan = _plan(supplied, voice)
        plan.update(
            {
                "direction": "stt",
                "transcript": supplied,
                "confidence": 1.0,
                "confidence_honesty": "REPORTED",
                "confidence_note": "operator supplied, not MEASURED",
            }
        )
        return seal(cell="N20", status="ok", payload=payload, output=plan)

    body = supplied or DEFAULT_TEXT
    plan = _plan(body, voice)
    plan["direction"] = "tts"
    if not supplied:
        plan["text_source"] = "default"
    return seal(cell="N20", status="ok", payload=payload, output=plan)
