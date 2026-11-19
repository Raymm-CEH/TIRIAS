from tirias.skill_system.gateway import SkillGateway
from tirias.skill_system.manager import SkillManager
from tirias.skill_system.web_skill import WebSearchSkill, parse_search_request


def build(tmp_path, granted=("network.read",), opener=None):
    opened = []
    manager = SkillManager()
    ok, errors = manager.register_skill(
        WebSearchSkill(opener=opener or opened.append)
    )
    assert ok, errors
    assert manager.enable_skill("web_search")
    gateway = SkillGateway(manager, granted, audit_path=tmp_path / "audit.log")
    return gateway, opened


def test_search_opens_encoded_url(tmp_path):
    gateway, opened = build(tmp_path)
    result = gateway.request("web_search", "search_web", {"query": "spotify"})
    assert result.allowed
    assert opened == ["https://duckduckgo.com/?q=spotify"]


def test_query_is_url_encoded_so_it_cannot_inject(tmp_path):
    gateway, opened = build(tmp_path)
    gateway.request("web_search", "search_web", {"query": "a&b=c #x --new-window"})
    assert opened == ["https://duckduckgo.com/?q=a%26b%3Dc+%23x+--new-window"]


def test_denied_without_network_permission(tmp_path):
    gateway, opened = build(tmp_path, granted=())
    result = gateway.request("web_search", "search_web", {"query": "spotify"})
    assert not result.allowed
    assert opened == []


def test_rejects_bad_queries(tmp_path):
    gateway, opened = build(tmp_path)
    for bad in ["", "x" * 201, "line\nbreak", "tab\there", 123]:
        assert not gateway.request("web_search", "search_web", {"query": bad}).allowed
    assert not gateway.request(
        "web_search", "search_web", {"query": "ok", "url": "file:///etc/passwd"}
    ).allowed
    assert opened == []


def test_browser_failure_is_reported(tmp_path):
    def broken(url):
        raise OSError("no browser")

    gateway, _ = build(tmp_path, opener=broken)
    result = gateway.request("web_search", "search_web", {"query": "spotify"})
    assert result.allowed
    assert result.message.startswith("Search failed")


def test_parse_search_requests():
    assert parse_search_request("search for spotify") == "spotify"
    assert parse_search_request("please search the web for cheap flights to Dubai?") == "cheap flights to Dubai"
    assert parse_search_request("open my browser and search for spotify") == "spotify"
    assert parse_search_request("google kes to zar") == "kes to zar"


def test_parse_ignores_normal_conversation():
    assert parse_search_request("what is a search engine") is None
    assert parse_search_request("search my documents for invoice") is None
    assert parse_search_request("open my browser") is None
    assert parse_search_request(None) is None
