from __future__ import absolute_import

import octoprint.plugin
from flask import jsonify, request, make_response
import json


class SpoolmanAPIPlugin(
    octoprint.plugin.SimpleApiPlugin, octoprint.plugin.StartupPlugin
):

    def __init__(self):
        super().__init__()
        self._spoolman_plugin = None

    def on_after_startup(self):
        """Called after server startup to get reference to Spoolman plugin"""
        self._logger.info("SpoolmanAPI plugin starting up...")

        # List all available plugins for debugging
        all_plugins = self._plugin_manager.get_plugins()
        self._logger.info(f"Available plugins: {list(all_plugins.keys())}")

        # Try different possible plugin identifiers
        possible_names = [
            "Spoolman",
            "spoolman",
            "octoprint_spoolman",
            "OctoPrint-Spoolman",
        ]

        for name in possible_names:
            self._logger.info(f"Trying to find plugin with identifier: {name}")

            # Try helpers first
            helpers = self._plugin_manager.get_helpers(name)
            if helpers:
                self._logger.info(f"Found helpers for {name}: {list(helpers.keys())}")
                self._spoolman_plugin_name = name
                self._spoolman_helpers = helpers
                break

            # Try direct plugin access
            plugin = self._plugin_manager.get_plugin(name)
            if plugin:
                self._logger.info(f"Found plugin {name} via direct access")
                self._spoolman_plugin = plugin
                self._spoolman_plugin_name = name

                # Log available methods
                methods = [
                    method for method in dir(plugin) if not method.startswith("_")
                ]
                self._logger.info(f"Available methods on {name}: {methods}")
                break

        if not self._spoolman_plugin and not hasattr(self, "_spoolman_helpers"):
            self._logger.error(
                "Could not find Spoolman plugin with any known identifier!"
            )

    def get_api_commands(self):
        return dict(
            set_spool=["spool_id", "tool"],
            get_current_spool=["tool"],
            list_tools=[],
            debug_info=[],
        )

    def on_api_command(self, command, data):
        if command == "debug_info":
            # Return debugging information
            all_plugins = list(self._plugin_manager.get_plugins().keys())

            debug_data = {
                "all_plugins": all_plugins,
                "spoolman_found": self._spoolman_plugin is not None
                or hasattr(self, "_spoolman_helpers"),
                "spoolman_plugin_name": getattr(self, "_spoolman_plugin_name", None),
            }

            if self._spoolman_plugin:
                debug_data["spoolman_methods"] = [
                    m for m in dir(self._spoolman_plugin) if not m.startswith("__")
                ]

            return jsonify(dict(success=True, debug=debug_data))

        elif command == "set_spool":
            spool_id = data.get("spool_id")
            tool = data.get("tool", 0)

            # Validate inputs
            if spool_id is None:
                return make_response(
                    jsonify(dict(success=False, error="spool_id is required")), 400
                )

            try:
                success = False
                method_used = None

                # Try helpers if available
                if hasattr(self, "_spoolman_helpers"):
                    self._logger.info(f"Trying helpers for spool selection")

                    # Common helper names
                    helper_methods = [
                        "select_spool",
                        "set_spool",
                        "set_active_spool",
                        "selectSpool",
                    ]

                    for method_name in helper_methods:
                        if method_name in self._spoolman_helpers:
                            self._logger.info(f"Using helper method: {method_name}")
                            result = self._spoolman_helpers[method_name](tool, spool_id)
                            success = True
                            method_used = f"helper.{method_name}"
                            break

                # Try direct plugin methods
                if not success and self._spoolman_plugin:
                    self._logger.info(f"Trying direct methods on plugin")

                    # Common method names for spool selection
                    method_names = [
                        "select_spool",
                        "selectSpool",
                        "set_spool",
                        "setSpool",
                        "set_active_spool",
                        "setActiveSpool",
                        "set_spool_selection",
                        "on_api_command",  # Some plugins handle it via API
                    ]

                    for method_name in method_names:
                        if hasattr(self._spoolman_plugin, method_name):
                            self._logger.info(f"Found method: {method_name}")
                            method = getattr(self._spoolman_plugin, method_name)

                            # Try different calling conventions
                            try:
                                if method_name == "on_api_command":
                                    # Try API command style
                                    result = method(
                                        "selectSpool",
                                        {"tool": tool, "spool": {"id": spool_id}},
                                    )
                                else:
                                    # Try direct call
                                    result = method(tool, spool_id)
                                success = True
                                method_used = f"direct.{method_name}"
                                break
                            except Exception as e:
                                self._logger.warning(
                                    f"Method {method_name} failed: {str(e)}"
                                )

                if not success:
                    return make_response(
                        jsonify(
                            dict(
                                success=False,
                                error="Could not find a way to set spool selection",
                            )
                        ),
                        503,
                    )

                # Fire event
                if self._event_bus:
                    self._event_bus.fire(
                        "plugin_spoolman_spool_selected",
                        {"tool": tool, "spool_id": spool_id},
                    )

                return jsonify(
                    dict(
                        success=success,
                        spool_id=spool_id,
                        tool=tool,
                        method_used=method_used,
                        message=f"Spool {spool_id} set for tool {tool}",
                    )
                )

            except Exception as e:
                self._logger.error(f"Error setting spool: {str(e)}", exc_info=True)
                return make_response(jsonify(dict(success=False, error=str(e))), 500)

        elif command == "get_current_spool":
            tool = data.get("tool", 0)

            try:
                spool_id = None

                # Try helpers
                if hasattr(self, "_spoolman_helpers"):
                    get_methods = [
                        "get_selected_spool",
                        "get_spool",
                        "getSelectedSpool",
                        "getSpool",
                    ]
                    for method_name in get_methods:
                        if method_name in self._spoolman_helpers:
                            spool_id = self._spoolman_helpers[method_name](tool)
                            break

                # Try direct methods
                if spool_id is None and self._spoolman_plugin:
                    method_names = [
                        "get_selected_spool",
                        "getSelectedSpool",
                        "get_spool_selection",
                    ]
                    for method_name in method_names:
                        if hasattr(self._spoolman_plugin, method_name):
                            try:
                                spool_id = getattr(self._spoolman_plugin, method_name)(
                                    tool
                                )
                                break
                            except:
                                pass

                return jsonify(dict(success=True, tool=tool, spool_id=spool_id))
            except Exception as e:
                self._logger.error(f"Error getting current spool: {str(e)}")
                return make_response(jsonify(dict(success=False, error=str(e))), 500)

        elif command == "list_tools":
            # Get printer profile to determine number of extruders
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
