"""The Visonic Alarm integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_time_interval,
    async_call_later,
)
import logging

from .const import DOMAIN, DOMAINCLIENT, DOMAINDATA, DOMAINCLIENTTASK
from .client import VisonicHandler


from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

# Define platform - alarm control panel
PLATFORMS: list[Platform] = [Platform.ALARM_CONTROL_PANEL]


# async def async_update_device_registry(hass, config_entry, client, data):
#     """Update device registry."""
#     device_registry = dr.async_get(hass)

#     device_registry.async_get_or_create(
#         config_entry_id=config_entry.entry_id,
#         connections={},
#         identifiers={(DOMAIN, vehicle.vin)},
#         manufacturer=data.vehicles[vehicle.vin].attributes.get("vehicleBrand"),
#         name=data.vehicles[vehicle.vin].attributes.get("nickname"),
#         model=data.vehicles[vehicle.vin].attributes.get("vehicleType"),
#         sw_version=data.vehicles[vehicle.vin].status.get("TU_STATUS_SW_VERSION_MAIN"),
#     )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Visonic Alarm from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    _LOGGER.debug("************* create connection here **************")

    # _LOGGER.info(f"Visonic Alarm entry.data={entry.data}")

    _LOGGER.info(
        f"Starting Visonic Alarm with entry id={entry.entry_id} (uuid={entry.data['uuid']})"
    )

    # create client and connect to the panel
    try:
        # Save the client ref
        client = VisonicHandler(hass, entry, entry.data["panel_id"])

        # Perform login sequence.
        await client.async_login()

        # After a small delay in letting the API server speak to the panel, attempt to get health data.
        # speeds up start time, only call if interval is greater than 30s.
        if entry.data["update_interval"] > 30:
            async_call_later(hass, 30, client.update)

        # Schedule periodic updates as defined by the user interval.
        update_tracker = async_track_time_interval(
            hass, client.update, timedelta(seconds=entry.data["update_interval"])
        )

        # update_tracker = async_track_time_interval(
        #     hass, client.update, timedelta(seconds=15)
        # )

        # Save the data for platforms to access.
        hass.data[DOMAIN][entry.entry_id] = {
            "client": client,
            "updates": update_tracker,
        }

        # Set up the actual alarm panel
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, "alarm_control_panel")
        )

        # entry.async_on_unload(entry.add_update_listener(update_listener))

        # return true to indicate success
        return True

    except Exception as error:
        _LOGGER.error("Visonic Panel could not be reached: [%s]", error)
        raise ConfigEntryNotReady

    return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN][entry.entry_id]["updates"]()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
