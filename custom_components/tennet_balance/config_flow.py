from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from .const import DOMAIN, CONF_KEEP_LAST_REGULATION_PRICES

class TennetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TennetOptionsFlowHandler(config_entry)

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
                vol.Required(CONF_KEEP_LAST_REGULATION_PRICES, default=False): bool,
            }),
            description_placeholders={
                "api_key": "An API key can be created via https://developer.tennet.eu/api-keys.\n\nMake sure the API key is created for the selected environment.\n\nTo create an API key, a developer account is required, which can be requested via https://developer.tennet.eu/register/. Approval of a developer account may take several days."
            }
        )


class TennetOptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        default_keep_last = self.config_entry.options.get(
            CONF_KEEP_LAST_REGULATION_PRICES,
            self.config_entry.data.get(CONF_KEEP_LAST_REGULATION_PRICES, False),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_KEEP_LAST_REGULATION_PRICES, default=default_keep_last): bool,
            }),
        )
