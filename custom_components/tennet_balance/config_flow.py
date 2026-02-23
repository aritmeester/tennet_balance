from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from homeassistant.helpers import selector

from .api import TennetApiClient, TennetApiAuthError
from .const import DOMAIN, CONF_KEEP_LAST_REGULATION_PRICES

class TennetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def _env_labels(self) -> dict[str, str]:
        language = (self.hass.config.language if self.hass else "en") or "en"
        if language.lower().startswith("nl"):
            return {
                "api": "Productie",
                "api.acc": "Acceptatie",
            }
        return {
            "api": "Production",
            "api.acc": "Acceptance",
        }

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TennetOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        env_labels = self._env_labels()

        if user_input is not None:
            environment = user_input["environment"]
            await self.async_set_unique_id(environment)
            self._abort_if_unique_id_configured()

            for entry in self._async_current_entries():
                if entry.data.get("environment") == environment:
                    return self.async_abort(reason="already_configured")

            environment_label = env_labels.get(environment, environment)
            return self.async_create_entry(
                title=f"TenneT Balance Delta ({environment_label})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("environment", default="api"): vol.In({k: v for k, v in env_labels.items()}),
                vol.Required("api_key", description={"suggested_value": ""}): str,
                vol.Required(CONF_KEEP_LAST_REGULATION_PRICES, default=False): bool,
            }),
            description_placeholders={
                "api_key": "An API key can be created via https://developer.tennet.eu/api-keys.\n\nMake sure the API key is created for the selected environment.\n\nTo create an API key, a developer account is required, which can be requested via https://developer.tennet.eu/register/. Approval of a developer account may take several days."
            }
        )

    async def async_step_reauth(self, entry_data):
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        if user_input is not None:
            api = TennetApiClient(
                self.hass,
                user_input["api_key"],
                self._reauth_entry.data["environment"],
            )
            try:
                await api.get_latest()
            except TennetApiAuthError:
                return self.async_show_form(
                    step_id="reauth_confirm",
                    data_schema=vol.Schema({
                        vol.Required("api_key"): str,
                    }),
                    errors={"base": "invalid_auth"},
                )
            except Exception:
                return self.async_show_form(
                    step_id="reauth_confirm",
                    data_schema=vol.Schema({
                        vol.Required("api_key"): str,
                    }),
                    errors={"base": "cannot_connect"},
                )

            return self.async_update_reload_and_abort(
                self._reauth_entry,
                data_updates={
                    "api_key": user_input["api_key"],
                },
            )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required("api_key"): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                }
            ),
        )


class TennetOptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            new_api_key = user_input.get("api_key", "").strip()
            if new_api_key and new_api_key != self.config_entry.data.get("api_key"):
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        **self.config_entry.data,
                        "api_key": new_api_key,
                    },
                )

            return self.async_create_entry(
                title="",
                data={
                    CONF_KEEP_LAST_REGULATION_PRICES: user_input[CONF_KEEP_LAST_REGULATION_PRICES],
                },
            )

        default_keep_last = self.config_entry.options.get(
            CONF_KEEP_LAST_REGULATION_PRICES,
            self.config_entry.data.get(CONF_KEEP_LAST_REGULATION_PRICES, False),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "api_key",
                    description={"suggested_value": ""},
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Required(CONF_KEEP_LAST_REGULATION_PRICES, default=default_keep_last): bool,
            }),
        )
