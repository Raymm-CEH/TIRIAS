"""Safe application launcher for TIRIAS."""

import shutil
import subprocess

from tirias.app_registry import get_application


class AppController:

    def launch(self, app_id: str) -> str:
        """Launch an approved application."""

        app = get_application(app_id)

        if app is None:
            return f"Blocked: {app_id} is not an approved application."

        executable = shutil.which(app.executable)

        if executable is None:
            return f"Unavailable: {app.name} executable was not found."

        try:
            subprocess.Popen(
                [executable],
                shell=False,
                start_new_session=True,
            )
            return f"Launch request sent: {app.name}."

        except OSError as error:
            return f"Launch failed: {error}"
