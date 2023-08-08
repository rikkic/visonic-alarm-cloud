from homeassistant.core import callback
from visonic import alarm
import logging


from datetime import timedelta

_LOGGER = logging.getLogger(__name__)


class VisonicHandler:
    def __init__(self, hass, config_entry, panel_id) -> None:
        self.hass = hass
        self.brand = ""
        self.model = ""
        self.entry = config_entry
        self.connected = False
        self.panel_status = None
        self.panel_info = None
        self.state = None
        self.client = None
        self.panel_id = panel_id
        self.code = ""
        self.codeless_arm = True
        self.codeless_disarm = False

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.brand} {self.model} ({self.panel_id})"

    async def async_login(self):
        self.client = await self.hass.async_add_executor_job(
            alarm.Setup, self.entry.data["host"], self.entry.data["uuid"]
        )

        _LOGGER.info(f"Successfully initialised client id={self.entry.entry_id}")

        # Log into the remote server
        await self.hass.async_add_executor_job(
            self.client.authenticate,
            self.entry.data["email"],
            self.entry.data["password"],
        )

        _LOGGER.info(f"Successfully authenticated id={self.entry.entry_id}")

        # Quick check to confirm panels are registered.
        panels = await self.hass.async_add_executor_job(self.client.get_panels)
        if panels:
            panel_ids = [panel.panel_serial for panel in panels]
            _LOGGER.info(f"Available panels={panel_ids}")

        _LOGGER.info(
            f"Attempt to log in to panel {self.panel_id} id={self.entry.entry_id}"
        )

        # Attempt to log into the panel
        await self.hass.async_add_executor_job(
            self.client.panel_login,
            self.entry.data["panel_id"],
            self.entry.data["master_code"],
        )

        self.codeless_arm = self.entry.data["codeless_arm"]
        self.codeless_disarm = self.entry.data["codeless_disarm"]
        self.code = self.entry.data["master_code"]

        # Get the panel info
        self.panel_info = await self.hass.async_add_executor_job(
            self.client.get_panel_info
        )
        self.brand = self.panel_info.manufacturer
        self.model = self.panel_info.model
        self.connected = True
        _LOGGER.info(f"Login successful for {self.unique_id} id={self.entry.entry_id}")

    @callback
    def update(self, *args):
        _LOGGER.info(f"Panel update for {self.panel_id}...")
        self.hass.async_create_task(self.async_update())

    async def async_update(self):
        # TODO wrap in try/except

        connected = await self.hass.async_add_executor_job(self.client.connected)
        if connected:
            self.connected = True
            # Perform actions in update, get the status from the panel
            self.panel_status = await self.hass.async_add_executor_job(
                self.client.get_status
            )
            # _LOGGER.info(f"Status: {self.panel_status}")
            # Map visonic fields to HA type fields.

            # TODO support multiple partitions
            self.state = self.panel_status.partitions[0].state
        else:
            self.connected = False

        _LOGGER.info(f"Panel update complete for {self.panel_id} (state={self.state})")
