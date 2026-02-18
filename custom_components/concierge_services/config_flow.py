"""Config flow for Concierge Services integration."""
from __future__ import annotations

import imaplib
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_IMAP_SERVER,
    CONF_IMAP_PORT,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SERVICES,
    DEFAULT_IMAP_PORT,
)
from .service_detector import detect_services_from_imap, DetectedService

_LOGGER = logging.getLogger(__name__)

# Configuration schema
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IMAP_SERVER, description={"suggested_value": "imap.gmail.com"}): str,
        vol.Required(CONF_IMAP_PORT, default=DEFAULT_IMAP_PORT): int,
        vol.Required(CONF_EMAIL, description={"suggested_value": "user@gmail.com"}): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_imap_connection(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the IMAP connection."""
    def _test_connection() -> bool:
        """Test IMAP connection in executor."""
        try:
            # Connect to IMAP server
            imap = imaplib.IMAP4_SSL(data[CONF_IMAP_SERVER], data[CONF_IMAP_PORT])
            
            # Try to authenticate
            imap.login(data[CONF_EMAIL], data[CONF_PASSWORD])
            
            # Logout if successful
            imap.logout()
            
            return True
        except imaplib.IMAP4.error as err:
            _LOGGER.error("IMAP authentication failed: %s", err)
            raise InvalidAuth from err
        except Exception as err:
            _LOGGER.error("IMAP connection failed: %s", err)
            raise CannotConnect from err
    
    # Run the connection test in executor to avoid blocking
    try:
        await hass.async_add_executor_job(_test_connection)
    except (CannotConnect, InvalidAuth):
        raise
    
    # Return info that can be used to create the entry
    return {"title": data[CONF_EMAIL]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Concierge Services."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._imap_data: dict[str, Any] = {}
        self._detected_services: list[DetectedService] = []

    async def async_step_user(  # type: ignore[override]
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Check if this email is already configured
            await self.async_set_unique_id(user_input[CONF_EMAIL])
            self._abort_if_unique_id_configured()
            
            try:
                await validate_imap_connection(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Store IMAP data and proceed to service selection
                self._imap_data = user_input
                return await self.async_step_services()

        return self.async_show_form(  # type: ignore[return-value]
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_services(  # type: ignore[override]
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle service selection step."""
        errors: dict[str, str] = {}
        
        # Detect services if not already done
        if not self._detected_services:
            try:
                self._detected_services = await self.hass.async_add_executor_job(
                    detect_services_from_imap,
                    self._imap_data[CONF_IMAP_SERVER],
                    self._imap_data[CONF_IMAP_PORT],
                    self._imap_data[CONF_EMAIL],
                    self._imap_data[CONF_PASSWORD],
                )
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error detecting services: %s", err)
                errors["base"] = "service_detection_failed"
        
        if user_input is not None:
            # Get selected services
            selected_services = user_input.get(CONF_SERVICES, [])
            
            # Build services metadata
            services_metadata = {}
            for svc in self._detected_services:
                if svc.service_id in selected_services:
                    services_metadata[svc.service_id] = {
                        "name": svc.service_name,
                        "sample_from": svc.sample_from,
                        "sample_subject": svc.sample_subject,
                    }
            
            # Combine IMAP data with selected services and metadata
            config_data = {
                **self._imap_data, 
                CONF_SERVICES: selected_services,
                "services_metadata": services_metadata,
            }
            
            # Create persistent notification for new services
            if selected_services:
                service_names = [services_metadata[sid]["name"] for sid in selected_services]
                service_list = "\n".join([f"- {name}" for name in service_names])
                
                await self.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "Concierge Services: New Services Detected",
                        "message": f"The following services have been configured:\n\n{service_list}\n\nEach service is now available as a device with its own sensor in Home Assistant.",
                        "notification_id": f"concierge_services_new_{self._imap_data[CONF_EMAIL].replace('@', '_').replace('.', '_')}",
                    },
                )
            
            return self.async_create_entry(  # type: ignore[return-value]
                title=self._imap_data[CONF_EMAIL],
                data=config_data,
            )
        
        # Create schema for service selection
        if self._detected_services:
            service_options = [
                selector.SelectOptionDict(
                    value=svc.service_id,
                    label=f"{svc.service_name} ({svc.email_count} emails)"
                )
                for svc in self._detected_services
            ]
            
            services_schema = vol.Schema(
                {
                    vol.Required(CONF_SERVICES, default=[svc.service_id for svc in self._detected_services]): 
                        selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=service_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.LIST,
                            )
                        ),
                }
            )
        else:
            # No services detected, allow user to continue without services
            services_schema = vol.Schema({})
            errors["base"] = "no_services_detected"
        
        return self.async_show_form(  # type: ignore[return-value]
            step_id="services",
            data_schema=services_schema,
            errors=errors,
            description_placeholders={
                "email": self._imap_data[CONF_EMAIL],
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
