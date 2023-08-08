"""Create a connection to a Visonic PowerMax or PowerMaster Alarm System (Alarm Panel Control)."""

from datetime import timedelta
import logging
import re
import voluptuous as vol

from homeassistant.auth.permissions.const import POLICY_CONTROL

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry

# Use the HA core attributes, alarm states and services
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMED,
    STATE_ALARM_PENDING,
    STATE_ALARM_TRIGGERED,
    STATE_UNKNOWN,
)

from homeassistant.core import HomeAssistant, valid_entity_id
from homeassistant.exceptions import HomeAssistantError, Unauthorized, UnknownUser
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers import entity_platform, service
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import VisonicHandler
from .const import DOMAIN, DOMAINCLIENT, DOMAINDATA

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the alarm control panel."""
    _LOGGER.info(
        "alarm control panel async_setup_entry called ****************************"
    )
    if DOMAIN in hass.data:
        # Get the client
        client = hass.data[DOMAIN][entry.entry_id]["client"]
        # Create the alarm controlpanel
        va = VisonicAlarmPanel(client)
        # Add it to HA
        devices = [va]
        async_add_entities(devices, True)

    platform = entity_platform.async_get_current_platform()
    _LOGGER.info("alarm control panel async_setup_entry called {0}".format(platform))


class VisonicAlarmPanel(alarm.AlarmControlPanelEntity):
    """Representation of a Visonic alarm control panel."""

    def __init__(self, client: VisonicHandler):
        """Initialize a Visonic security alarm."""
        _LOGGER.info(f"Initialising alarm control panel... client: {client}")
        self._client = client
        self._mystate = STATE_UNKNOWN  # TODO
        self._myname = self._client.unique_id
        _LOGGER.debug("Initialising alarm control panel {0}".format(self._myname))
        self._device_state_attributes = {}
        self._users = {}
        self._doneUsers = False
        self._last_triggered = ""
        self._dispatcher = f"VISONIC_{self._client.panel_id}"
        self._panel = self._client.panel_id

    async def async_added_to_hass(self):
        """Register callbacks."""
        # Register for dispatcher calls to update the state
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._dispatcher, self.onChange)
        )

    async def async_will_remove_from_hass(self):
        """Remove from hass."""
        await super().async_will_remove_from_hass()
        self._client = None
        _LOGGER.debug("alarm control panel async_will_remove_from_hass")

    def onChange(self, event_id: int, datadictionary: dict):
        """HA Event Callback."""
        self.schedule_update_ha_state(True)

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._client.unique_id

    @property
    def name(self):
        """Return the name of the alarm."""
        return self._client.unique_id

    @property
    def changed_by(self):
        """Last change triggered by."""
        return self._last_triggered

    @property
    def device_info(self):
        """Return information about the device."""
        if self._client is not None:
            return {
                "manufacturer": self._client.brand,
                "identifiers": {(DOMAIN, self._myname)},
                "name": self._myname,
                "model": self._client.model,
                # "via_device" : (DOMAIN, "Visonic Intruder Alarm"),
            }
        return {
            "manufacturer": "Visonic",
            "identifiers": {(DOMAIN, self._myname)},
            "name": f"Visonic Alarm Panel {self._panel})",
            "model": None,
            # "model": "Alarm Panel",
            # "via_device" : (DOMAIN, "Visonic Intruder Alarm"),
        }

    # @property
    # def code_arm_required(self):
    #     """Whether the code is required for arm actions."""
    #     if self._client is not None:
    #         return not self._client.isArmWithoutCode()
    #     return True

    def update(self):
        """Get the state of the device."""
        self._mystate = STATE_UNKNOWN

        if self._client.connected:
            _LOGGER.info(f"Update {self._myname}, state: {self._client.state}")
            if self._client.state == "DISARM":
                self._mystate = STATE_ALARM_DISARMED
            elif self._client.state == "AWAY":
                self._mystate = STATE_ALARM_ARMED_AWAY
            elif self._client.state == "HOME":
                self._mystate = STATE_ALARM_ARMED_HOME
            else:
                _LOGGER.info(f"Unkown alarm state: {self._client.state}")
                self._mystate = STATE_UNKNOWN

        _LOGGER.info(f"Update {self._myname}, hass alarm state: {self._mystate}")

    @property
    def state(self):
        """Return the state of the device."""
        return self._mystate

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        retval = 0  # No features, supported.

        if self._client.connected:
            _LOGGER.info(f"Update {self._myname}, state: {self._client.state}")
            if self._mystate == STATE_ALARM_DISARMED:
                retval = retval | AlarmControlPanelEntityFeature.ARM_HOME
                retval = retval | AlarmControlPanelEntityFeature.ARM_AWAY
            elif self._mystate == STATE_ALARM_ARMED_AWAY:
                pass  # Don't think you can switch modes
            elif self._mystate == STATE_ALARM_ARMED_HOME:
                pass  # Don't think you can switch modes

        return retval

    # DO NOT OVERRIDE state_attributes AS IT IS USED IN THE LOVELACE FRONTEND TO DETERMINE code_format

    @property
    def code_format(self):
        """Regex for code format or None if no code is required."""
        if self._client.connected:
            _LOGGER.info(
                f"code state {self._mystate}, codeless_arm = {self._client.codeless_arm}, codeless_disarm = {self._client.codeless_disarm}"
            )
            if self._mystate == STATE_ALARM_DISARMED and self._client.codeless_arm:
                _LOGGER.info(f"1")
                # Alarm disarmed, allow codeless arm
                return None
            elif (
                self._mystate == STATE_ALARM_DISARMED and not self._client.codeless_arm
            ):
                # Alarm disarmed, codeless arm disallowed
                _LOGGER.info(f"2")
                return CodeFormat.NUMBER
            elif self._mystate != STATE_ALARM_DISARMED and self._client.codeless_disarm:
                # Alarm armed, codeless disarm allowed
                _LOGGER.info(f"3")
                return None
            elif self._mystate != STATE_ALARM_DISARMED and self._client.codeless_disarm:
                # Alarm armed, codeless disarm disallowed
                _LOGGER.info(f"4")
                return CodeFormat.NUMBER
            else:
                # Safe catchall.
                _LOGGER.info(f"5")
                return CodeFormat.NUMBER
        return CodeFormat.NUMBER

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        if not self._client.connected:
            raise HomeAssistantError(
                f"Visonic Integration {self._myname} not connected to panel."
            )
        self._client.client.disarm()

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        if not self._client.connected:
            raise HomeAssistantError(
                f"Visonic Integration {self._myname} not connected to panel."
            )
        self._client.client.arm_home()

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        if not self._client.connected:
            raise HomeAssistantError(
                f"Visonic Integration {self._myname} not connected to panel."
            )
        self._client.client.arm_away()

    def alarm_trigger(self, code=None):
        """Send alarm trigger command."""
        _LOGGER.debug("Alarm Panel Trigger Not Yet Implemented")
        raise NotImplementedError()

    def alarm_arm_custom_bypass(self, data=None):
        """Bypass Panel."""
        _LOGGER.debug("Alarm Panel Custom Bypass Not Yet Implemented")
        raise NotImplementedError()
