"""Web search skill: opens a search in the approved browser. Runs only via the gateway."""

import re
import shutil
import subprocess
from urllib.parse import quote_plus

from tirias.app_registry import get_application
from tirias.skill_system.interface import ActionSpec, Skill, SkillManifest

SEARCH_URL = "https://duckduckgo.com/?q="
MAX_QUERY_CHARS = 200
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

_SEARCH_REQUEST = re.compile(
    r"^(?:please\s+)?"
    r"(?:(?:open|launch|start)\s+(?:my\s+|the\s+)?(?:web\s+)?(?:browser|firefox)\s+and\s+)?"
    r"(?:search(?:\s+(?:the\s+web|online|google))?\s+for|google)\s+"
    r"(.+?)[.?!]*$",
    re.IGNORECASE,
)


def parse_search_request(text):
    """Return the search query if the text is an explicit web-search command, else None."""
    if not isinstance(text, str):
        return None
    match = _SEARCH_REQUEST.match(text.strip())
    if not match:
        return None
    query = " ".join(match.group(1).split())
    return query[:MAX_QUERY_CHARS] or None


def _open_in_firefox(url):
    app = get_application("firefox")
    executable = shutil.which(app.executable) if app else None
    if executable is None:
        raise OSError("Firefox was not found.")
    subprocess.Popen(
        [executable, url],
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


class WebSearchSkill(Skill):
    """Open a web search in the approved browser."""

    def __init__(self, opener=None):
        self._open = opener

    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            skill_id="web_search",
            name="Web Search",
            version="1.0.0",
            description="Open a web search in the approved browser.",
            permissions=("network.read",),
        )

    def available_actions(self) -> tuple[str, ...]:
        return ("search_web",)

    def action_specs(self) -> dict:
        return {
            "search_web": ActionSpec(
                permission="network.read",
                schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_QUERY_CHARS,
                            "pattern": r"^[^\x00-\x1f\x7f]+$",
                        }
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            )
        }

    def execute(self, action: str, arguments: dict) -> str:
        if action != "search_web":
            return "Rejected: unsupported web action."
        if not isinstance(arguments, dict) or set(arguments) != {"query"}:
            return "Rejected: provide only a query argument."
        query = arguments["query"]
        if (
            not isinstance(query, str)
            or not query.strip()
            or len(query) > MAX_QUERY_CHARS
            or _CONTROL_CHARS.search(query)
        ):
            return "Rejected: invalid search query."
        try:
            (self._open or _open_in_firefox)(SEARCH_URL + quote_plus(query.strip()))
        except OSError as error:
            return f"Search failed: {error}"
        return "Search request sent."
