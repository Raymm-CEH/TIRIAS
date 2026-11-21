"""Turn explicit spoken or typed system commands into gateway requests.

Only whole-sentence matches count, so ordinary conversation never triggers an action.
"""

import re

_MEDIA_NOUN = r"(?: music| song| video| playback| media)?"


def _clean(text):
    text = re.sub(r"[.!?,]+", " ", str(text).casefold())
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(?:please |can you |could you |would you )+", "", text)
    return re.sub(r" please$", "", text)


def _fixed(skill, action, arguments=None):
    return lambda _match: (skill, action, dict(arguments or {}))


def _clamped(skill, action, name, low, high):
    return lambda match: (skill, action, {name: max(low, min(high, int(match.group(1))))})


_RULES = [
    (r"pause(?: (?:the|my))?(?: (?:music|song|video|playback|media))?",
     _fixed("media_control", "pause")),
    (r"stop the (?:music|song|video|playback|media)", _fixed("media_control", "pause")),
    (rf"(?:play|resume){_MEDIA_NOUN}", _fixed("media_control", "play")),
    (r"(?:play )?(?:the )?next (?:song|track)|skip(?: the)?(?: song| track)?",
     _fixed("media_control", "next_track")),
    (r"(?:play )?(?:the )?(?:previous|last) (?:song|track)|go back a (?:song|track)",
     _fixed("media_control", "previous_track")),
    (r"unmute(?: the)?(?: sound| volume| audio)?", _fixed("volume_control", "set_mute", {"muted": False})),
    (r"mute(?: the)?(?: sound| volume| audio)?", _fixed("volume_control", "set_mute", {"muted": True})),
    (r"(?:turn (?:the )?volume up|volume up|turn it up|louder|(?:increase|raise|turn up) (?:the )?volume)",
     _fixed("volume_control", "change_volume", {"delta": 10})),
    (r"(?:turn (?:the )?volume down|volume down|turn it down|quieter|softer|(?:decrease|lower|reduce|turn down) (?:the )?volume)",
     _fixed("volume_control", "change_volume", {"delta": -10})),
    (r"(?:set (?:the )?)?volume (?:to |at )?(\d{1,3})(?: percent|%)?",
     _clamped("volume_control", "set_volume", "level", 0, 100)),
    (r"(?:turn (?:the )?brightness up|brightness up|brighter|(?:increase|raise) (?:the )?brightness|make (?:it|the screen) brighter)",
     _fixed("brightness_control", "change_brightness", {"delta": 10})),
    (r"(?:turn (?:the )?brightness down|brightness down|dimmer|darker|(?:decrease|lower|reduce) (?:the )?brightness|make (?:it|the screen) (?:dimmer|darker))",
     _fixed("brightness_control", "change_brightness", {"delta": -10})),
    (r"(?:set (?:the )?)?brightness (?:to |at )?(\d{1,3})(?: percent|%)?",
     _clamped("brightness_control", "set_brightness", "percent", 5, 100)),
]
_COMPILED = [(re.compile(pattern), build) for pattern, build in _RULES]


def parse_system_request(text):
    """Return (skill_id, action, arguments) for an explicit system command, else None."""
    cleaned = _clean(text)
    if not cleaned:
        return None
    for pattern, build in _COMPILED:
        match = pattern.fullmatch(cleaned)
        if match:
            return build(match)
    return None
