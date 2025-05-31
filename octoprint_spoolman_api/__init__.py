# Copyright 2025 William Marchesi

# Author: William Marchesi
# Email: will@marchesi.io
# Website: https://marchesi.io/

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding=utf-8
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

        if plugin_info and plugin_info.implementation:
            self._spoolman_impl = plugin_info.implementation
            self._logger.info("Got Spoolman implementation successfully")

            # Try to find the settings key constant
            # The plugin likely has a SettingsKeys class or similar
            if hasattr(self._spoolman_impl, "SettingsKeys"):
                self._settings_keys = self._spoolman_impl.SettingsKeys
                self._logger.info("Found SettingsKeys")
            else:
                # Try to find it in the module
                import inspect

                module = inspect.getmodule(self._spoolman_impl)
                if hasattr(module, "SettingsKeys"):
                    self._settings_keys = module.SettingsKeys
                    self._logger.info("Found SettingsKeys in module")
                else:
                    self._settings_keys = None
                    self._logger.warning("Could not find SettingsKeys")
        else:
            self._logger.error("Spoolman plugin not found or has no implementation!")
            self._spoolman_impl = None

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

            if not self._spoolman_impl:
                return make_response(
                    jsonify(dict(success=False, error="Spoolman plugin not available")),
                    503,
                )

            try:
                # Convert spool_id to string as the plugin expects
                spool_id_str = str(spool_id) if spool_id is not None else None
                tool_id = int(tool)

                # Get the current spools settings
                # Try to use the SettingsKeys if we found it
                if self._settings_keys and hasattr(
                    self._settings_keys, "SELECTED_SPOOL_IDS"
                ):
                    settings_key = self._settings_keys.SELECTED_SPOOL_IDS
                else:
                    # Fallback to common key names
                    settings_key = "selectedSpoolIds"

                # Get current spools from Spoolman plugin settings
                spools = self._spoolman_impl._settings.get([settings_key])
                if spools is None:
                    spools = {}

                # Update the spool selection
                spools[str(tool_id)] = {
                    "spoolId": spool_id_str,
                }

                # Save to Spoolman plugin settings
                self._spoolman_impl._settings.set([settings_key], spools)
                self._spoolman_impl._settings.save()

                # Trigger the plugin event
                # Try to use the Events enum if available
                event_name = None
                if hasattr(self._spoolman_impl, "Events"):
                    events = self._spoolman_impl.Events
                    if hasattr(events, "PLUGIN_SPOOLMAN_SPOOL_SELECTED"):
                        event_name = events.PLUGIN_SPOOLMAN_SPOOL_SELECTED

                if not event_name:
                    # Try module level
                    import inspect

                    module = inspect.getmodule(self._spoolman_impl)
                    if hasattr(module, "Events"):
                        events = module.Events
                        if hasattr(events, "PLUGIN_SPOOLMAN_SPOOL_SELECTED"):
                            event_name = events.PLUGIN_SPOOLMAN_SPOOL_SELECTED

                if not event_name:
                    # Fallback to string
                    event_name = "plugin_spoolman_spool_selected"

                # Trigger the event using the Spoolman plugin's method
                if hasattr(self._spoolman_impl, "triggerPluginEvent"):
                    self._spoolman_impl.triggerPluginEvent(
                        event_name,
                        {
                            "toolIdx": tool_id,
                            "spoolId": spool_id_str,
                        },
                    )
                else:
                    # Use the event bus directly
                    self._event_bus.fire(
                        event_name,
                        {
                            "toolIdx": tool_id,
                            "spoolId": spool_id_str,
                        },
                    )

                self._logger.info(
                    f"Successfully set spool {spool_id_str} for tool {tool_id}"
                )

                return jsonify(
                    dict(
                        success=True,
                        spool_id=spool_id_str,
                        tool=tool_id,
                        message=f"Spool {spool_id_str} set for tool {tool_id}",
                    )
                )

            except Exception as e:
                self._logger.error(f"Error setting spool: {str(e)}", exc_info=True)
                return make_response(
                    jsonify(
                        dict(success=False, error=f"Failed to set spool: {str(e)}")
                    ),
                    500,
                )

        elif command == "get_current_spool":
            tool = data.get("tool", 0)
            tool_id = str(int(tool))

            if not self._spoolman_impl:
                return jsonify(dict(success=True, tool=tool, spool_id=None))

            try:
                # Get the settings key
                if self._settings_keys and hasattr(
                    self._settings_keys, "SELECTED_SPOOL_IDS"
                ):
                    settings_key = self._settings_keys.SELECTED_SPOOL_IDS
                else:
                    settings_key = "selectedSpoolIds"

                # Get current spools from settings
                spools = self._spoolman_impl._settings.get([settings_key])

                if spools and tool_id in spools:
                    spool_data = spools[tool_id]
                    spool_id = (
                        spool_data.get("spoolId")
                        if isinstance(spool_data, dict)
                        else spool_data
                    )

                    return jsonify(
                        dict(success=True, tool=int(tool), spool_id=spool_id)
                    )

                return jsonify(dict(success=True, tool=int(tool), spool_id=None))

            except Exception as e:
                self._logger.error(f"Error getting current spool: {str(e)}")
                return jsonify(dict(success=True, tool=int(tool), spool_id=None))

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
