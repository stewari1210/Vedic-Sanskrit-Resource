"""
Phonetically-faithful Sanskrit pronunciation for the tutor.

Three engines, in quality/availability order:

  1. espeak   -- eSpeak-NG. It has NO Sanskrit voice, so we route through the
                 most schwa-faithful Indic voice available (default: Kannada, via
                 Devanagari->Kannada -- Dravidian scripts pronounce every inherent
                 vowel; the same trick Vagdhenu uses). CPU-only, offline, free,
                 deployable on Streamlit Cloud via packages.txt (`espeak-ng`).
                 Robotic but PHONETICALLY CORRECT (keeps schwas, vowel length,
                 retroflexes, ḷ) -- unlike a Hindi prose TTS.
  2. vagdhenu -- Prof. Prathosh's Vāgdhenu chant TTS (Apache-2.0), called
                 remotely via its Hugging Face Space (needs their GPU). Real
                 metrical chant (pārāyaṇa) quality. Best for whole verses.
  3. gtts     -- Google TTS (Hindi voice). Legacy fallback only; schwa-deletes.

ACCENT SAFETY (hard requirement)
--------------------------------
Vedic *svara* marks (udātta/anudātta/svarita) and IAST length diacritics must
survive the pronunciation path. Nothing here calls `remove_diacritics`, and the
only text cleaning done (`clean_for_speech`) strips *punctuation, verse markers
and digits only* -- never a letter, a combining accent mark, or a length sign.
`assert_accents_preserved()` and the __main__ self-test verify this.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import unicodedata
from typing import Optional, Tuple

try:  # project logger if available, else stdlib
    from src.helper import logger
except Exception:  # pragma: no cover
    import logging
    logger = logging.getLogger("pronunciation")


# --------------------------------------------------------------------------
# Accent / diacritic protection
# --------------------------------------------------------------------------
# Codepoints that carry Vedic accent or vowel-quality information and must
# NEVER be stripped by this module.
_ACCENT_CODEPOINTS = frozenset(
    [0x0951, 0x0952]                    # ॑ udātta, ॒ anudātta (Devanagari)
    + list(range(0x1CD0, 0x1D00))       # Vedic Extensions (svarita marks, etc.)
    + list(range(0xA8E0, 0xA900))       # Devanagari Extended (combining Vedic)
    + [0x0300, 0x0301, 0x0302, 0x0304]  # combining grave/acute/circumflex/macron
)                                       # (used when accents ride on romanization)


def has_vedic_accents(text: str) -> bool:
    """True if the text carries any Vedic svara / accent mark."""
    return any(ord(ch) in _ACCENT_CODEPOINTS for ch in text)


def _accent_signature(text: str) -> str:
    """The subsequence of accent-bearing codepoints, for before/after checks."""
    return "".join(ch for ch in text if ord(ch) in _ACCENT_CODEPOINTS)


def assert_accents_preserved(before: str, after: str) -> None:
    """Raise if any accent mark present in `before` was lost in `after`."""
    if _accent_signature(before) != _accent_signature(after):
        raise AssertionError(
            "Pronunciation pipeline dropped Vedic accent marks: "
            f"{_accent_signature(before)!r} -> {_accent_signature(after)!r}"
        )


# --------------------------------------------------------------------------
# Cleaning (accent-safe): remove ONLY markers / punctuation / digits
# --------------------------------------------------------------------------
_VERSE_MARKER = re.compile(r"॥[^॥]*॥")          # e.g. "॥ RV 1.1.1 ॥" citation blocks
_DROP_CHARS = re.compile(
    r"[।॥|/\\\[\]{}()<>*_#0-9०-९]"     # dandas, brackets, ASCII+Devanagari digits
)


def clean_for_speech(text: str) -> str:
    """
    Strip verse markers, dandas, brackets and digits so the synthesiser reads
    words, not citations. Letters, conjuncts, IAST length diacritics and every
    Vedic accent mark are preserved verbatim.
    """
    if not text:
        return ""
    t = _VERSE_MARKER.sub(" ", text)
    t = _DROP_CHARS.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip()
    assert_accents_preserved(text, t)   # guarantee: accents survived
    return t


# --------------------------------------------------------------------------
# Small config shim (Streamlit secrets / env), no hard dependency
# --------------------------------------------------------------------------
def _cfg(key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        from src.config import get_config_value
        val = get_config_value(key, default)
        return val if val not in (None, "") else default
    except Exception:
        return os.environ.get(key, default)


def _to_devanagari_keep_accents(text: str) -> str:
    """
    Best-effort IAST/romanized -> Devanagari for engines that want Devanagari
    (Vāgdhenu). If already Devanagari, returned unchanged. Accents that don't
    survive transliteration are re-appended so the signature is preserved.
    """
    if any(0x0900 <= ord(c) <= 0x097F for c in text):
        return text
    try:
        from indic_transliteration import sanscript
        out = sanscript.transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
    except Exception as e:
        logger.warning(f"IAST->Devanagari failed, using raw text: {e}")
        return text
    # If transliteration dropped accents, keep the original as a safer carrier.
    if _accent_signature(text) and not _accent_signature(out):
        logger.info("Transliteration dropped accents; preserving original for chant engine.")
        return text
    return out


# --------------------------------------------------------------------------
# Engine 1: eSpeak-NG Sanskrit voice
# --------------------------------------------------------------------------
def espeak_available() -> Optional[str]:
    """Return the espeak binary name if installed, else None."""
    return shutil.which("espeak-ng") or shutil.which("espeak")


# eSpeak-NG has NO Sanskrit voice. These are the best Sanskrit *proxies that
# actually exist* and, unlike Hindi, do not delete the inherent schwa.
# Order = most to least faithful:
#   kn  Kannada  -- fed via Devanagari->Kannada; Dravidian scripts voice EVERY
#                   inherent vowel (the same routing trick Vagdhenu uses).
#   mr  Marathi  -- Devanagari-native, keeps most schwas, has the Vedic ḷ (ळ).
#   ne  Nepali   -- Devanagari-native.
#   hi  Hindi    -- last resort; schwa-deletes (the thing we're avoiding).
_ESPEAK_VOICE_ORDER = ["kn", "mr", "ne", "hi"]


def _espeak_voice_codes(binary: str) -> set:
    """Language codes eSpeak actually has installed (col 2 of --voices)."""
    try:
        out = subprocess.run(
            [binary, "--voices"], capture_output=True, timeout=10
        ).stdout.decode("utf-8", "ignore")
        codes = set()
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                codes.add(parts[1])
        return codes
    except Exception:
        return set()


def _resolve_espeak_voice(binary: str) -> str:
    """Pick the most schwa-faithful available voice (ESPEAK_VOICE overrides)."""
    pref = _cfg("ESPEAK_VOICE", None)
    order = ([pref] if pref else []) + _ESPEAK_VOICE_ORDER
    available = _espeak_voice_codes(binary)
    for code in order:
        if code and (not available or code in available):
            return code
    return "hi"


def _to_kannada(text: str) -> str:
    """Devanagari/IAST -> Kannada script for the schwa-faithful Kannada voice."""
    if any(0x0C80 <= ord(c) <= 0x0CFF for c in text):
        return text
    src = _to_devanagari_keep_accents(text)
    try:
        from indic_transliteration import sanscript
        return sanscript.transliterate(src, sanscript.DEVANAGARI, sanscript.KANNADA)
    except Exception as e:
        logger.warning(f"Devanagari->Kannada failed: {e}")
        return src


def synthesize_espeak(text: str, slow: bool = True) -> Optional[bytes]:
    """
    Render Sanskrit to WAV via eSpeak-NG. Since eSpeak has no Sanskrit voice, we
    use the most schwa-faithful Indic voice available (default: Kannada, fed via
    Devanagari->Kannada routing so every inherent vowel is pronounced -- this is
    what fixes the Hindi schwa-deletion that made the old audio wrong). Override
    with the ESPEAK_VOICE config key (e.g. "mr" for Devanagari-native Marathi).
    """
    binary = espeak_available()
    if not binary:
        logger.info("eSpeak-NG not found on PATH; skipping espeak engine.")
        return None
    voice = _resolve_espeak_voice(binary)
    spoken = _to_kannada(text) if voice == "kn" else _to_devanagari_keep_accents(text)
    speed = "125" if slow else "160"
    try:
        proc = subprocess.run(
            [binary, "-v", voice, "-s", speed, "--stdout"],
            input=spoken.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0 or not proc.stdout:
            logger.warning(
                f"eSpeak (-v {voice}) failed rc={proc.returncode}: {proc.stderr[:200]!r}"
            )
            return None
        logger.info(f"eSpeak rendered Sanskrit via '{voice}' voice.")
        return proc.stdout  # WAV bytes (RIFF header included)
    except Exception as e:
        logger.warning(f"eSpeak invocation error: {e}")
        return None


# --------------------------------------------------------------------------
# Engine 2: Vāgdhenu chant TTS via its Hugging Face Space (remote GPU)
# --------------------------------------------------------------------------
def synthesize_vagdhenu(
    text: str, meter: Optional[str] = None, space: Optional[str] = None
) -> Optional[bytes]:
    """
    Call Prof. Prathosh's Vāgdhenu HF Space for metrical chant audio.

    NOTE: the exact endpoint name / argument order of the Space can change.
    Confirm them on the Space's "Use via API" panel and set VAGDHENU_API /
    VAGDHENU_SPACE (env or Streamlit secrets) if the defaults below are wrong.
    On any failure this returns None so callers fall back to eSpeak.
    """
    try:
        from gradio_client import Client
    except ImportError:
        logger.info("gradio_client not installed; skipping Vāgdhenu engine.")
        return None

    space = space or _cfg("VAGDHENU_SPACE", "prathoshap/vagdhenu-demo")
    api_name = _cfg("VAGDHENU_API", None)   # None => let gradio pick the endpoint
    deva = _to_devanagari_keep_accents(text)

    try:
        client = Client(space)
    except Exception as e:
        logger.warning(f"Vāgdhenu Space '{space}' unreachable: {e}")
        return None

    arg_sets = ([deva, meter] if meter else [deva]), [deva]
    last_err: Optional[Exception] = None
    for args in arg_sets:
        try:
            result = client.predict(*args, api_name=api_name) if api_name \
                else client.predict(*args)
            path = result[0] if isinstance(result, (list, tuple)) else result
            if isinstance(path, dict):          # gradio may return {"name"/"path": ...}
                path = path.get("path") or path.get("name")
            with open(path, "rb") as fh:
                return fh.read()
        except Exception as e:
            last_err = e
    logger.warning(
        f"Vāgdhenu predict failed (confirm VAGDHENU_API on the Space). Last: {last_err}"
    )
    return None


# --------------------------------------------------------------------------
# Engine 3: gTTS (legacy fallback)
# --------------------------------------------------------------------------
def synthesize_gtts(text: str, lang: str = "hi") -> Optional[bytes]:
    """Google TTS -> MP3 bytes. Hindi voice schwa-deletes; fallback only."""
    try:
        from gtts import gTTS
    except ImportError:
        logger.info("gTTS not installed.")
        return None
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang=lang, slow=True).write_to_fp(buf)
        buf.seek(0)
        data = buf.read()
        return data or None
    except Exception as e:
        logger.warning(f"gTTS failed: {e}")
        return None


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------
DEFAULT_ENGINE = "espeak"
_MIME = {"espeak": "audio/wav", "vagdhenu": "audio/wav", "gtts": "audio/mpeg"}


def synthesize(
    text: str, engine: Optional[str] = None, lang: str = "hi", meter: Optional[str] = None
) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """
    Return (audio_bytes, mime_type, engine_used). Accent marks in `text` are
    preserved through cleaning; each engine then handles them as best it can.
    Falls back down the chain (chosen -> espeak -> gtts) so something always
    plays; `engine_used` reports which one actually produced the audio, so the
    UI can tell the user when it silently fell back.

    engine: "espeak" (default) | "vagdhenu" | "gtts"
    """
    if not text or not text.strip():
        return None, None, None
    engine = (engine or _cfg("TTS_ENGINE", DEFAULT_ENGINE) or DEFAULT_ENGINE).lower()
    spoken = clean_for_speech(text)   # accent-safe (asserts internally)

    order = {
        "vagdhenu": ["vagdhenu", "espeak", "gtts"],
        "espeak": ["espeak", "gtts"],
        "gtts": ["gtts", "espeak"],
    }.get(engine, ["espeak", "gtts"])

    for eng in order:
        if eng == "espeak":
            audio = synthesize_espeak(spoken)
        elif eng == "vagdhenu":
            audio = synthesize_vagdhenu(text, meter=meter)  # pass full accented text
        else:
            audio = synthesize_gtts(spoken, lang=lang)
        if audio:
            if eng != engine:
                logger.info(f"Pronunciation engine '{engine}' unavailable; used '{eng}'.")
            return audio, _MIME[eng], eng
    return None, None, None


# --------------------------------------------------------------------------
# Self-test: accents must survive; report engine availability
# --------------------------------------------------------------------------
if __name__ == "__main__":
    # RV 1.1.1 opening with accent marks: anudātta (॒) + udātta (॑) + Vedic ḷ (ळ)
    sample = "अ॒ग्निमी॑ळे पु॒रोहि॑तं य॒ज्ञस्य॑ दे॒वमृत्वि॒जम्"
    print("Sample:", sample)
    print("NFC codepoints:", [hex(ord(c)) for c in unicodedata.normalize("NFC", sample)][:12], "…")
    print("has_vedic_accents:", has_vedic_accents(sample))

    cleaned = clean_for_speech("॥ RV 1.1.1 ॥ " + sample + " ॥ 1 ॥")
    print("cleaned         :", cleaned)
    print("accent signature before:", _accent_signature(sample))
    print("accent signature after :", _accent_signature(cleaned))
    assert has_vedic_accents(cleaned), "FAIL: accents stripped by cleaning!"
    assert "ळ" in cleaned, "FAIL: Vedic ḷ lost!"
    assert_accents_preserved(sample, cleaned)
    print("ACCENT-PRESERVATION SELF-TEST: PASS ✓")

    print("\nEngine availability:")
    _bin = espeak_available()
    if _bin:
        _v = _resolve_espeak_voice(_bin)
        print(f"  eSpeak-NG : {_bin}  (Sanskrit routed via '{_v}' voice)")
        print(f"              Kannada routing sample: {_to_kannada(sample)}")
    else:
        print("  eSpeak-NG : NOT INSTALLED (apt/brew install espeak-ng)")
    try:
        import gradio_client  # noqa
        print("  gradio_client : installed (Vāgdhenu callable)")
    except ImportError:
        print("  gradio_client : NOT installed (pip install gradio_client)")
