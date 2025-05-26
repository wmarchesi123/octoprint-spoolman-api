from __future__ import absolute_import

import octoprint.plugin
from flask import jsonify, request, make_response


class SpoolmanAPIPlugin(
    octoprint.plugin.SimpleApiPlugin, octoprint.plugin.StartupPlugin
):

    def on_after_startup(self):
        """Called after server startup"""
        self._logger.info("SpoolmanAPI plugin starting up...")

        # The plugin identifier from the repository
        plugin_id = "Spoolman"

        # Get the plugin info
        plugin_info = self._plugin_manager.get_plugin_info(plugin_id)

        if plugin_info:
            self._logger.info(f"Found Spoolman plugin info!")

            # Get the actual implementation
            if plugin_info.implementation:
                self._spoolman_impl = plugin_info.implementation
                self._logger.info(f"Got Spoolman implementation")

                # List available methods
                methods = [m for m in dir(self._spoolman_impl) if not m.startswith("_")]
                self._logger.info(f"Available public methods: {methods}")
            else:
                self._logger.error("Spoolman plugin has no implementation")
                self._spoolman_impl = None
        else:
            self._logger.error("Spoolman plugin not found!")
            self._spoolman_impl = None

        # Also try to get helpers
        helpers = self._plugin_manager.get_helpers(plugin_id)
        if helpers:
            self._logger.info(f"Found Spoolman helpers: {list(helpers.keys())}")
            self._spoolman_helpers = helpers
        else:
            self._logger.info("No Spoolman helpers found")
            self._spoolman_helpers = None

    def get_api_commands(self):
        return dict(
            set_spool=["spool_id", "tool"],
            get_current_spool=["tool"],
            list_tools=[],
            debug_info=[],
        )

    def on_api_command(self, command, data):
        if command == "debug_info":
            info = {
                "spoolman_found": self._spoolman_impl is not None,
                "helpers_found": self._spoolman_helpers is not None,
            }

            if self._spoolman_impl:
                info["methods"] = [
                    m for m in dir(self._spoolman_impl) if not m.startswith("_")
                ]

            if self._spoolman_helpers:
                info["helpers"] = list(self._spoolman_helpers.keys())

            return jsonify(dict(success=True, debug=info))

        elif command == "set_spool":
            spool_id = data.get("spool_id")
            tool = data.get("tool", 0)

            if spool_id is None:
                return make_response(
                    jsonify(dict(success=False, error="spool_id is required")), 400
                )

            # First try helpers if available
            if self._spoolman_helpers:
                # Common helper method names
                for method_name in ["select_spool", "set_spool", "set_active_spool"]:
                    if method_name in self._spoolman_helpers:
                        try:
                            self._logger.info(
                                f"Calling helper {method_name}({tool}, {spool_id})"
                            )
                            result = self._spoolman_helpers[method_name](tool, spool_id)

                            return jsonify(
                                dict(
                                    success=True,
                                    spool_id=spool_id,
                                    tool=tool,
                                    method=f"helper.{method_name}",
                                    message=f"Spool {spool_id} set for tool {tool}",
                                )
                            )
                        except Exception as e:
                            self._logger.error(f"Helper {method_name} failed: {e}")

            # Try the implementation directly
            if self._spoolman_impl:
                # Check if it has on_api_command (for handling API calls)
                if hasattr(self._spoolman_impl, "on_api_command"):
                    try:
                        # Try different command formats that Spoolman might use
                        commands_to_try = [
                            ("select_spool", {"tool": tool, "spool_id": spool_id}),
                            ("selectSpool", {"tool": tool, "spool": {"id": spool_id}}),
                            ("set_spool", {"tool": tool, "spool_id": spool_id}),
                        ]

                        for cmd, payload in commands_to_try:
                            self._logger.info(
                                f"Trying API command: {cmd} with {payload}"
                            )
                            result = self._spoolman_impl.on_api_command(cmd, payload)

                            if result:  # Assuming non-None/non-False means success
                                return jsonify(
                                    dict(
                                        success=True,
                                        spool_id=spool_id,
                                        tool=tool,
                                        method=f"api_command.{cmd}",
                                        message=f"Spool {spool_id} set for tool {tool}",
                                    )
                                )
                    except Exception as e:
                        self._logger.error(f"API command failed: {e}")

                # Try direct method calls
                method_names = ["select_spool", "selectSpool", "set_spool", "setSpool"]
                for method_name in method_names:
                    if hasattr(self._spoolman_impl, method_name):
                        try:
                            self._logger.info(
                                f"Calling method {method_name}({tool}, {spool_id})"
                            )
                            method = getattr(self._spoolman_impl, method_name)
                            result = method(tool, spool_id)

                            return jsonify(
                                dict(
                                    success=True,
                                    spool_id=spool_id,
                                    tool=tool,
                                    method=f"direct.{method_name}",
                                    message=f"Spool {spool_id} set for tool {tool}",
                                )
                            )
                        except Exception as e:
                            self._logger.error(f"Method {method_name} failed: {e}")

            # Last resort - try updating settings
            if self._spoolman_impl and hasattr(self._spoolman_impl, "_settings"):
                try:
                    self._logger.info("Trying to update via settings")
                    self._spoolman_impl._settings.set([f"tool{tool}_spool"], spool_id)
                    self._spoolman_impl._settings.save()

                    return jsonify(
                        dict(
                            success=True,
                            spool_id=spool_id,
                            tool=tool,
                            method="settings",
                            message=f"Spool {spool_id} set for tool {tool} via settings",
                        )
                    )
                except Exception as e:
                    self._logger.error(f"Settings update failed: {e}")

            return make_response(
                jsonify(
                    dict(
                        success=False,
                        error="Could not find a way to set spool selection",
                    )
                ),
                503,
            )

        elif command == "get_current_spool":
            tool = data.get("tool", 0)
            spool_id = None

            # Try helpers first
            if self._spoolman_helpers:
                for method_name in [
                    "get_selected_spool",
                    "get_spool",
                    "getSelectedSpool",
                ]:
                    if method_name in self._spoolman_helpers:
                        try:
                            spool_id = self._spoolman_helpers[method_name](tool)
                            break
                        except Exception as e:
                            self._logger.error(f"Helper {method_name} failed: {e}")

            # Try implementation methods
            if spool_id is None and self._spoolman_impl:
                for method_name in [
                    "get_selected_spool",
                    "getSelectedSpool",
                    "get_spool",
                ]:
                    if hasattr(self._spoolman_impl, method_name):
                        try:
                            method = getattr(self._spoolman_impl, method_name)
                            spool_id = method(tool)
                            break
                        except Exception as e:
                            self._logger.error(f"Method {method_name} failed: {e}")

            # Try settings
            if (
                spool_id is None
                and self._spoolman_impl
                and hasattr(self._spoolman_impl, "_settings")
            ):
                try:
                    spool_id = self._spoolman_impl._settings.get([f"tool{tool}_spool"])
                except:
                    pass

            return jsonify(dict(success=True, tool=tool, spool_id=spool_id))

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
