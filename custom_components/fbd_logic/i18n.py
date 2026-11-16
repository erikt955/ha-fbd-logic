"""Language support.

The integration is written in Norwegian. Every other language gets English: `EN` in i18n_en.py maps
each Norwegian text to its English version, so a text is looked up by the Norwegian original.

- The block library follows the language of the user who opens the panel (sent with the request).
- Messages made inside HA (warnings on save, block errors, entity names) follow HA's system language,
  set with `set_language()` when the integration starts.
"""

from __future__ import annotations

import re
from typing import Any

from .i18n_en import EN

_NORWEGIAN = re.compile(r"^(nb|nn|no)([-_]|$)", re.IGNORECASE)
_language = "nb"


def language_for(code: str | None) -> str:
    """'nb' for Norwegian (nb, nn, no, nb-NO …), otherwise 'en'."""
    return "nb" if code and _NORWEGIAN.match(code) else "en"


def set_language(code: str | None) -> None:
    global _language  # noqa: PLW0603 - one HA instance per process
    _language = language_for(code)


def current_language() -> str:
    return _language


def tr(text: str, lang: str | None = None, **values: Any) -> str:
    """Translate a Norwegian text (a str.format template when values are given)."""
    if (lang or _language) == "en":
        text = EN.get(text, text)
    return text.format(**values) if values else text


def translate_block(block: dict[str, Any], lang: str) -> dict[str, Any]:
    """Translate the texts of one built-in block (library_json format) in place."""
    if lang != "en":
        return block
    for key in ("title", "description"):
        block[key] = EN.get(block[key], block[key])
    for port in block["inputs"] + block["outputs"]:
        if port.get("label"):
            port["label"] = EN.get(port["label"], port["label"])
    for param in block["params"]:
        for key in ("label", "help"):
            if param.get(key):
                param[key] = EN.get(param[key], param[key])
        for opt in param.get("options") or []:
            opt["label"] = EN.get(opt["label"], opt["label"])
        for opt in param.get("suggest") or []:
            opt["label"] = EN.get(opt["label"], opt["label"])
        # Default names for new blocks ("Settpunkt" → "Setpoint"); select values are never translated.
        if param["type"] in ("text", "textarea") and isinstance(param.get("default"), str):
            param["default"] = EN.get(param["default"], param["default"])
    return block
