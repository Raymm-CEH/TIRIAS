"""Approved application registry for TIRIAS."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Application:
    app_id: str
    name: str
    executable: str


APPROVED_APPLICATIONS = {
    "firefox": Application(
        app_id="firefox",
        name="Firefox ESR",
        executable="/usr/lib/firefox-esr/firefox-esr",
    ),
    "mousepad": Application(
        app_id="mousepad",
        name="Mousepad",
        executable="/usr/bin/mousepad",
    ),
    "thunar": Application(
        app_id="thunar",
        name="Thunar File Manager",
        executable="/usr/bin/thunar",
    ),
    "terminal": Application(
        app_id="terminal",
        name="Terminal",
        executable="/usr/bin/x-terminal-emulator",
    ),
    "settings": Application(
        app_id="settings",
        name="Settings Manager",
        executable="/usr/bin/xfce4-settings-manager",
    ),
}


def get_application(app_id: str) -> Application | None:
    """Return an approved application, or None if not registered."""
    return APPROVED_APPLICATIONS.get(app_id.lower().strip())


def list_applications() -> list[Application]:
    """Return all approved applications."""
    return list(APPROVED_APPLICATIONS.values())
