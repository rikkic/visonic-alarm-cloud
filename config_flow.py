"""Config flow for Visonic Alarm integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
import uuid
from visonic import alarm

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host", default="visonic.tycomonitor.com"): str,
        vol.Required("email"): str,
        vol.Required("password"): str,
        vol.Required("panel_id"): str,
        vol.Required("master_code"): str,
        vol.Optional("codeless_arm", default=True): bool,
        vol.Optional("codeless_disarm", default=False): bool,
        vol.Required("update_interval", default=60): int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    try:
        # Connect to remote server
        client = await hass.async_add_executor_job(
            alarm.Setup, data["host"], data["uuid"]
        )
    except Exception as err:
        raise CannotConnect(f"{err}") from err

    try:
        # Log into the remote server
        await hass.async_add_executor_job(
            client.authenticate, data["email"], data["password"]
        )
    except Exception as err:
        raise InvalidAuth(f"{err}") from err

    # Return info that you want to store in the config entry.
    return {"title": f"Alarm Panel ({data['panel_id']})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Visonic Alarm."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Generate a UUID for the data before creating the entry - will allow for testing auth under the same UUID as the created entry.
            user_input["uuid"] = str(uuid.uuid4())
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create the entry.
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        # self.options = dict(config_entry.options)
        self.options = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        data_schema = vol.Schema(
            {
                vol.Required("host", default=self.options.get("host")): str,
                vol.Required("email", default=self.options.get("email")): str,
                vol.Required("password", default=self.options.get("password")): str,
                vol.Required("panel_id", default=self.options.get("panel_id")): str,
                vol.Required("master_code", default=""): str,
                vol.Optional(
                    "codeless_arm",
                    default=self.options.get("codeless_arm", False),
                ): bool,
                vol.Optional(
                    "codeless_disarm",
                    default=self.options.get("codeless_disarm", False),
                ): bool,
                vol.Required(
                    "update_interval",
                    default=self.options.get("update_interval"),
                ): int,
            }
        )
        if user_input is not None:
            # Generate a UUID for the data before creating the entry - will allow for testing auth under the same UUID as the created entry.
            user_input["uuid"] = str(uuid.uuid4())
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create the entry.
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
