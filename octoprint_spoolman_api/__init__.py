from __future__ import absolute_import

import octoprint.plugin
from flask import jsonify, request, make_response


class SpoolmanAPIPlugin(
    octoprint.plugin.SimpleApiPlugin, octoprint.plugin.StartupPlugin
):

    def on_after_startup(self):
        """Called after server startup"""
        self._logger.info("SpoolmanAPI plugin starting up...")

        plugin_id = "Spoolman"

        self._spoolman_plugin = self._plugin_manager.get_plugin(plugin_id)

        if self._spoolman_plugin:
            self._logger.info(f"Found Spoolman plugin!")
            if hasattr(self._spoolman_plugin, "_impl"):
                impl = self._spoolman_plugin._impl
                methods = [m for m in dir(impl) if not m.startswith("_")]
                self._logger.info(f"Available methods: {methods}")
        else:
            self._logger.error("Spoolman plugin not found!")

    def get_api_commands(self):
        return dict(
            set_spool=["spool_id", "tool"], get_current_spool=["tool"], list_tools=[]
        )

    def on_api_command(self, command, data):
        if command == "set_spool":
            spool_id = data.get("spool_id")
            tool = data.get("tool", 0)

            if spool_id is None:
                return make_response(
                    jsonify(dict(success=False, error="spool_id is required")), 400
                )

            if self._spoolman_plugin and hasattr(self._spoolman_plugin, "_impl"):
                impl = self._spoolman_plugin._impl

                if hasattr(impl, "on_api_command"):
                    try:
                        result = impl.on_api_command(
                            "select_spool", {"tool": tool, "spool_id": spool_id}
                        )

                        return jsonify(
                            dict(
                                success=True,
                                spool_id=spool_id,
                                tool=tool,
                                message=f"Spool {spool_id} set for tool {tool}",
                            )
                        )
                    except Exception as e:
                        self._logger.error(f"Error calling Spoolman API: {e}")

                try:
                    plugin_settings = impl._settings
                    plugin_settings.set([f"tool{tool}_spool"], spool_id)
                    plugin_settings.save()

                    return jsonify(
                        dict(
                            success=True,
                            spool_id=spool_id,
                            tool=tool,
                            message=f"Spool {spool_id} set for tool {tool} via settings",
                        )
                    )
                except Exception as e:
                    self._logger.error(f"Error updating settings: {e}")

            return make_response(
                jsonify(
                    dict(
                        success=False,
                        error="Could not set spool - Spoolman plugin not accessible",
                    )
                ),
                503,
            )

        elif command == "get_current_spool":
            tool = data.get("tool", 0)

            if self._spoolman_plugin and hasattr(self._spoolman_plugin, "_impl"):
                impl = self._spoolman_plugin._impl

                try:
                    plugin_settings = impl._settings
                    spool_id = plugin_settings.get([f"tool{tool}_spool"])

                    return jsonify(dict(success=True, tool=tool, spool_id=spool_id))
                except Exception as e:
                    self._logger.error(f"Error reading settings: {e}")

            return jsonify(dict(success=True, tool=tool, spool_id=None))

        elif command == "list_tools":
            printer_profile = self._printer_profile_manager.get_current()
            extruder_count = printer_profile.get("extruder", {}).get("count", 1)

            tools = []
            for i in range(extruder_count):
                tools.append({"id": i, "name": f"Tool {i}"})

            return jsonify(dict(success=True, tools=tools))

        return make_response("Unknown command", 400)

    def is_api_adminonly(self):
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
