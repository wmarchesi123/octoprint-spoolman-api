# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from flask import jsonify, request, make_response
import json


class SpoolmanAPIPlugin(octoprint.plugin.SimpleApiPlugin):

    def __init__(self):
        super().__init__()
        self._spoolman_plugin = None

    def on_after_startup(self):
        """Called after server startup to get reference to Spoolman plugin"""
        self._logger.info("SpoolmanAPI plugin starting up...")

        # Get reference to the Spoolman plugin
        helpers = self._plugin_manager.get_helpers(
            "Spoolman", "select_spool", "get_selected_spool"
        )
        if helpers:
            self._logger.info("Found Spoolman plugin helpers")
            if "select_spool" in helpers:
                self._select_spool = helpers["select_spool"]
            if "get_selected_spool" in helpers:
                self._get_selected_spool = helpers["get_selected_spool"]
        else:
            # If helpers aren't available, try direct access
            self._logger.info("No Spoolman helpers found, trying direct access")
            spoolman_plugin = self._plugin_manager.get_plugin("Spoolman")
            if spoolman_plugin:
                self._spoolman_plugin = spoolman_plugin
                self._logger.info("Found Spoolman plugin via direct access")
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

            # Validate inputs
            if spool_id is None:
                return make_response(
                    jsonify(dict(success=False, error="spool_id is required")), 400
                )

            try:
                # Try to use the Spoolman plugin's method if available
                if hasattr(self, "_select_spool"):
                    self._logger.info(
                        f"Using Spoolman helper to set spool {spool_id} for tool {tool}"
                    )
                    result = self._select_spool(tool, spool_id)
                    success = result is not False
                elif self._spoolman_plugin:
                    # Try direct method call
                    self._logger.info(
                        f"Using direct method to set spool {spool_id} for tool {tool}"
                    )

                    # Common patterns for spool selection in OctoPrint plugins
                    if hasattr(self._spoolman_plugin, "select_spool"):
                        result = self._spoolman_plugin.select_spool(tool, spool_id)
                        success = True
                    elif hasattr(self._spoolman_plugin, "set_spool_selection"):
                        result = self._spoolman_plugin.set_spool_selection(
                            tool, spool_id
                        )
                        success = True
                    elif hasattr(self._spoolman_plugin, "_on_select_spool"):
                        result = self._spoolman_plugin._on_select_spool(tool, spool_id)
                        success = True
                    else:
                        # Try to update the data directly
                        self._logger.info(
                            "No direct methods found, attempting data update"
                        )

                        # Check if plugin has spool_selections data
                        if hasattr(self._spoolman_plugin, "_spool_selections"):
                            self._spoolman_plugin._spool_selections[str(tool)] = (
                                spool_id
                            )
                            success = True
                        else:
                            # Last resort: try to trigger via settings
                            self._logger.info("Attempting to update via settings")
                            settings_data = {f"tool{tool}_spool": spool_id}
                            self._settings.set(settings_data, force=True)
                            success = True
                else:
                    return make_response(
                        jsonify(
                            dict(success=False, error="Spoolman plugin not available")
                        ),
                        503,
                    )

                # Trigger any necessary events
                eventManager = self._event_bus
                if eventManager:
                    eventManager.fire(
                        "SpoolSelectionChanged", {"tool": tool, "spool_id": spool_id}
                    )

                return jsonify(
                    dict(
                        success=success,
                        spool_id=spool_id,
                        tool=tool,
                        message=f"Spool {spool_id} set for tool {tool}",
                    )
                )

            except Exception as e:
                self._logger.error(f"Error setting spool: {str(e)}")
                return make_response(jsonify(dict(success=False, error=str(e))), 500)

        elif command == "get_current_spool":
            tool = data.get("tool", 0)

            try:
                if hasattr(self, "_get_selected_spool"):
                    spool_id = self._get_selected_spool(tool)
                elif self._spoolman_plugin and hasattr(
                    self._spoolman_plugin, "_spool_selections"
                ):
                    spool_id = self._spoolman_plugin._spool_selections.get(str(tool))
                else:
                    spool_id = None

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
