"""
sms_parser.py — SMS keyword parsing engine for Dehati-Connect.

Supports two intents:

1. REGISTER  — a worker registers themselves:
     REGISTER <name> <skill> <location>
     Examples:
       "REGISTER Ram Lal Tractor Mechanic Ramnagar"
       "PANJIYAN Suresh Kumar Plumber Ballia"

2. SEARCH    — a farmer/caller asks for a worker:
     NEED <skill> [<location>]
     Examples:
       "NEED Tractor Mechanic"
       "CHAHIYE Plumber Vaishali"
       "Need wall builder Patna"

Any message that cannot be matched is classified as UNKNOWN and the caller
receives a usage hint.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Keyword maps  (Hindi SMS keywords → canonical intent)
# ---------------------------------------------------------------------------

REGISTER_KEYWORDS = {
    "register", "reg", "panjiyan", "panjikaran", "add",
}

SEARCH_KEYWORDS = {
    "need", "chahiye", "search", "dhundo", "find", "khojo",
}

# Skill aliases → canonical skill tag stored in the database.
# Entries support partial matching so "tractor" → "tractor mechanic".
SKILL_ALIASES: dict[str, str] = {
    "tractor mechanic":  "tractor mechanic",
    "tractor":           "tractor mechanic",
    "mechanic":          "mechanic",
    "mistri":            "mason",
    "mason":             "mason",
    "diwaar":            "mason",
    "wall":              "mason",
    "plumber":           "plumber",
    "electrician":       "electrician",
    "bijli":             "electrician",
    "mazdoor":           "labourer",
    "labour":            "labourer",
    "laborer":           "labourer",
    "fasal":             "harvesting",
    "harvest":           "harvesting",
    "harvesting":        "harvesting",
    "carpenter":         "carpenter",
    "barhai":            "carpenter",
    "painter":           "painter",
    "rangai":            "painter",
    "welder":            "welder",
    "welding":           "welder",
    "pump":              "pump operator",
    "pump operator":     "pump operator",
    "driver":            "driver",
}


# ---------------------------------------------------------------------------
# Parsed result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ParsedSMS:
    intent: str                   # "REGISTER" | "SEARCH" | "UNKNOWN"
    raw: str                      # original message text

    # REGISTER fields
    name: Optional[str]     = None
    phone: Optional[str]    = None   # caller's phone, set by the caller layer

    # Shared
    skill: Optional[str]    = None   # canonical skill tag
    location: Optional[str] = None

    errors: list = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# Main parsing function
# ---------------------------------------------------------------------------

def parse_sms(text: str, sender_phone: str = "") -> ParsedSMS:
    """
    Parse an incoming SMS and return a :class:`ParsedSMS` with intent and
    extracted fields.
    """
    raw = text.strip()
    tokens = _tokenize(raw)

    if not tokens:
        return ParsedSMS(intent="UNKNOWN", raw=raw,
                         errors=["Empty message"])

    first = tokens[0].lower()

    if first in REGISTER_KEYWORDS:
        return _parse_register(raw, tokens[1:], sender_phone)

    if first in SEARCH_KEYWORDS:
        return _parse_search(raw, tokens[1:])

    # Last-chance: try to detect a search intent without the keyword
    skill = _extract_skill(tokens)
    if skill:
        location = _extract_location_from_tokens(tokens, skill)
        return ParsedSMS(intent="SEARCH", raw=raw,
                         skill=skill, location=location)

    return ParsedSMS(intent="UNKNOWN", raw=raw,
                     errors=["Could not determine intent"])


# ---------------------------------------------------------------------------
# Intent-specific parsers
# ---------------------------------------------------------------------------

def _parse_register(raw: str, rest: list, phone: str) -> ParsedSMS:
    """
    Expected format after keyword:  <Name…> <skill…> <location…>

    Strategy: scan from the end of the token list — the last contiguous
    block that does not match a skill alias is treated as the location;
    the preceding skill match is extracted; everything before is the name.
    """
    result = ParsedSMS(intent="REGISTER", raw=raw, phone=phone)

    if len(rest) < 3:
        result.errors.append(
            "Format: REGISTER <Name> <Skill> <Location>  "
            "Example: REGISTER Ram Lal Tractor Mechanic Ramnagar"
        )
        return result

    skill, skill_start, skill_end = _find_skill_in_tokens(rest)
    if not skill:
        result.errors.append(
            "Skill not recognised. Known skills: " + ", ".join(sorted(set(SKILL_ALIASES.values())))
        )
        return result

    name_tokens = rest[:skill_start]
    location_tokens = rest[skill_end:]

    if not name_tokens:
        result.errors.append("Name missing. Format: REGISTER <Name> <Skill> <Location>")
        return result

    if not location_tokens:
        result.errors.append("Location missing. Format: REGISTER <Name> <Skill> <Location>")
        return result

    result.name = " ".join(name_tokens)
    result.skill = skill
    result.location = " ".join(location_tokens)
    return result


def _parse_search(raw: str, rest: list) -> ParsedSMS:
    """
    Expected format after keyword:  <skill…> [<location…>]
    """
    result = ParsedSMS(intent="SEARCH", raw=raw)

    if not rest:
        result.errors.append(
            "Format: NEED <Skill> [Location]  "
            "Example: NEED Tractor Mechanic Ramnagar"
        )
        return result

    skill, skill_start, skill_end = _find_skill_in_tokens(rest)
    if not skill:
        # fall back: treat the whole rest as the skill keyword
        result.skill = " ".join(rest).lower()
        return result

    result.skill = skill
    location_tokens = rest[skill_end:]
    if location_tokens:
        result.location = " ".join(location_tokens)
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list:
    return re.split(r"\s+", text.strip())


def _extract_skill(tokens: list) -> Optional[str]:
    """Try to find a skill alias anywhere in the token list."""
    skill, _, _ = _find_skill_in_tokens(tokens)
    return skill


def _find_skill_in_tokens(tokens: list):
    """
    Slide a window of 1-3 words over *tokens* and return the first
    (canonical_skill, start_index, end_index) match, or (None, -1, -1).
    """
    lower = [t.lower() for t in tokens]
    for window in (3, 2, 1):
        for i in range(len(lower) - window + 1):
            phrase = " ".join(lower[i: i + window])
            if phrase in SKILL_ALIASES:
                return SKILL_ALIASES[phrase], i, i + window
    return None, -1, -1


def _extract_location_from_tokens(tokens: list, skill: str) -> Optional[str]:
    skill_tokens = skill.split()
    lower = [t.lower() for t in tokens]
    for i in range(len(lower) - len(skill_tokens) + 1):
        if lower[i: i + len(skill_tokens)] == skill_tokens:
            rest = tokens[i + len(skill_tokens):]
            return " ".join(rest) if rest else None
    return None
