# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from flask import jsonify, request, make_response


class SpoolmanAPIPlugin(octoprint.plugin.SimpleApiPlugin):

    def get_api_commands(self):
        return dict(set_spool=["spool_id", "tool"])

    def on_api_command(self, command, data):
        if command == "set_spool":
            spool_id = data.get("spool_id")
            tool = data.get("tool", 0)

            # TODO: Implement the actual spool setting logic
            # For now, just return success
            self._logger.info(f"Setting spool {spool_id} for tool {tool}")

            return jsonify(
                dict(
                    success=True,
                    spool_id=spool_id,
                    tool=tool,
                    message=f"Spool {spool_id} set for tool {tool}",
                )
            )

        return make_response("Unknown command", 400)

    def is_api_adminonly(self):
        # Set to False to allow any authenticated user
        # Set to True to require admin privileges
        return False

    def get_update_information(self):
        return {
            "spoolman_api": {
                "displayName": "Spoolman API",
                "displayVersion": self._plugin_version,
                "type": "github_release",
                "user": "wmarchesi123",
                "repo": "octoprint-spoolman-api",
                "current": self._plugin_version,
                "pip": "https://github.com/wmarchesi123/octoprint-spoolman-api/archive/{target_version}.zip",
            }
        }


__plugin_name__ = "Spoolman API"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SpoolmanAPIPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
