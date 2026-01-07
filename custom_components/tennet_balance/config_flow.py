from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class TennetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="TenneT Balance Delta", data=user_input)

        ENV_LABELS = {
            "api": "Production",
            "api.acc": "Acceptance"
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("environment", default="api"): vol.In({k: v for k, v in ENV_LABELS.items()}),
                vol.Required("api_key", description={"suggested_value": ""}): str,
            }),
            description_placeholders={
                "api_key": "An API key can be created via https://developer.tennet.eu/api-keys.\n\nMake sure the API key is created for the selected environment.\n\nTo create an API key, a developer account is required, which can be requested via https://developer.tennet.eu/register/. Approval of a developer account may take several days."
            }
        )
