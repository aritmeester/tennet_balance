from copy import deepcopy
from datetime import timedelta
import logging
from time import monotonic
from zoneinfo import ZoneInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
import homeassistant.util.dt as dt_util
import asyncio

from .const import REGULATION_PRICE_KEYS
from .api import TennetApiAuthError, TennetApiError

LOGGER = logging.getLogger(__name__)

MIN_UPDATE_INTERVAL = 6  # coalesce healthy refreshes; HTTP limits live in the API client
ISP_MINUTES = 15
MARKET_TIMEZONE = ZoneInfo("Europe/Amsterdam")
# Consecutive auth failures tolerated after first success before triggering reauth.
AUTH_FAILURE_THRESHOLD = 5
# Grace window in which a failed update keeps last-known data (entities stay available).
UPDATE_GRACE_SECONDS = 180

_CACHE_MISS = object()


def _parse_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _has_price(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def _isp_start_for(dt_value):
    minute = (dt_value.minute // ISP_MINUTES) * ISP_MINUTES
    return dt_value.replace(minute=minute, second=0, microsecond=0)


def _as_local_datetime(dt_value):
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=dt_util.UTC)
    return dt_value.astimezone(MARKET_TIMEZONE)


def _regulation_state_code(has_upward: bool, has_downward: bool) -> int:
    if has_upward and has_downward:
        return 2
    if has_upward:
        return 1
    if has_downward:
        return -1
    return 0

class TennetCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, keep_last_regulation_prices: bool = False, *, config_entry=None):
        super().__init__(
            hass, LOGGER, config_entry=config_entry,
            name="TenneT Balance Delta", update_interval=timedelta(seconds=12),
        )
        self.api = api
        self._keep_last_regulation_prices = keep_last_regulation_prices
        self._last_success_monotonic = None
        self._update_lock = asyncio.Lock()  # ensures only one fetch at a time
        self._last_known_values = {}
        self._api_last_success = None
        self._api_last_failure = None
        self._api_response_time_ms = None
        self._api_consecutive_failures = 0
        self._api_consecutive_auth_failures = 0
        self._api_last_error = None
        self._api_last_error_details = None
        self._cached_payload = _CACHE_MISS
        self._cached_latest_point = _CACHE_MISS
        self._cached_isp_analysis = _CACHE_MISS

    def _ensure_payload_cache(self):
        """Invalidate derived values when the coordinator publishes a new payload."""
        if self.data is not self._cached_payload:
            self._cached_payload = self.data
            self._cached_latest_point = _CACHE_MISS
            self._cached_isp_analysis = _CACHE_MISS

    def _within_update_grace(self) -> bool:
        if self._last_success_monotonic is None or self.data is None:
            return False
        elapsed = monotonic() - self._last_success_monotonic
        return elapsed <= UPDATE_GRACE_SECONDS

    def _extract_latest_point(self, data):
        try:
            return data["Response"]["TimeSeries"][0]["Period"][0]["points"][-1]
        except (KeyError, IndexError, TypeError):
            return None

    def _extract_all_points(self, data):
        points = []
        try:
            time_series = data["Response"]["TimeSeries"]
        except (KeyError, TypeError):
            return points

        for series in time_series:
            for period in series.get("Period", []):
                period_points = period.get("points", [])
                if isinstance(period_points, list):
                    points.extend(period_points)
        return points

    def _point_interval(self, point):
        start = None
        end = None

        raw_start = point.get("timeInterval_start")
        if raw_start:
            parsed_start = dt_util.parse_datetime(raw_start)
            if parsed_start is not None:
                start = _as_local_datetime(parsed_start)

        raw_end = point.get("timeInterval_end")
        if raw_end:
            parsed_end = dt_util.parse_datetime(raw_end)
            if parsed_end is not None:
                end = _as_local_datetime(parsed_end)

        return start, end

    def _direction_activations_for_point(self, point):
        upward_power = _parse_float(point.get("power_afrr_in")) + _parse_float(point.get("power_mfrrda_in"))
        downward_power = _parse_float(point.get("power_afrr_out")) + _parse_float(point.get("power_mfrrda_out"))

        up_price_present = _has_price(point.get("max_upw_regulation_price"))
        down_price_present = _has_price(point.get("min_downw_regulation_price"))

        afrr_up_active = _parse_float(point.get("power_afrr_in")) > 0 and up_price_present
        afrr_down_active = _parse_float(point.get("power_afrr_out")) > 0 and down_price_present
        mfrr_up_active = _parse_float(point.get("power_mfrrda_in")) > 0
        mfrr_down_active = _parse_float(point.get("power_mfrrda_out")) > 0

        upward_active = upward_power > 0 and (afrr_up_active or mfrr_up_active)
        downward_active = downward_power > 0 and (afrr_down_active or mfrr_down_active)

        return upward_active, downward_active

    def _analyse_isp_points(self, points):
        has_upward = False
        has_downward = False
        for point in points:
            up_active, down_active = self._direction_activations_for_point(point)
            has_upward = has_upward or up_active
            has_downward = has_downward or down_active
            if has_upward and has_downward:
                break
        regulation_state = _regulation_state_code(has_upward, has_downward)
        return {
            "has_upward": has_upward,
            "has_downward": has_downward,
            "regulation_state": regulation_state,
            "is_regulation_state_2": has_upward and has_downward,
            "sample_count": len(points),
        }

    def _group_points_by_isp(self, points):
        grouped = {}
        for point in points:
            start, end = self._point_interval(point)
            if start is None and end is None:
                continue

            if start is not None:
                reference = start
            elif end is not None:
                reference = end - timedelta(seconds=1)
            else:
                continue
            isp_start = _isp_start_for(reference)
            sort_ts = end if end is not None else start
            grouped.setdefault(isp_start, []).append((sort_ts, point))

        for isp_start in grouped:
            grouped[isp_start].sort(key=lambda item: item[0])
            grouped[isp_start] = [item[1] for item in grouped[isp_start]]

        return grouped

    def _rule_state_2_window_analysis(self):
        """Reuse the ISP analysis for the currently published payload."""
        self._ensure_payload_cache()
        if self._cached_isp_analysis is _CACHE_MISS:
            self._cached_isp_analysis = self._calculate_rule_state_2_window_analysis()
        return self._cached_isp_analysis

    def _calculate_rule_state_2_window_analysis(self):
        all_points = self._extract_all_points(self.data)
        if not all_points:
            return None

        grouped = self._group_points_by_isp(all_points)

        latest_point = None
        latest_end = None
        for point in all_points:
            _start, end = self._point_interval(point)
            if end is None:
                continue
            if latest_end is None or end > latest_end:
                latest_end = end
                latest_point = point

        if latest_end is None or latest_point is None:
            return None

        latest_start, _latest_end = self._point_interval(latest_point)
        reference = latest_start if latest_start is not None else (latest_end - timedelta(seconds=1))
        current_isp_start = _isp_start_for(reference)
        previous_isp_start = current_isp_start - timedelta(minutes=ISP_MINUTES)

        current_points = grouped.get(current_isp_start, [])
        previous_points = grouped.get(previous_isp_start, [])

        current_analysis = self._analyse_isp_points(current_points)
        previous_analysis = self._analyse_isp_points(previous_points)

        return {
            "current_isp_start": current_isp_start.isoformat(),
            "current_isp_prediction": current_analysis,
            "previous_isp_start": previous_isp_start.isoformat(),
            "previous_isp": previous_analysis,
            "latest_interval_end": latest_end.isoformat(),
        }

    @property
    def rule_state_2_previous_isp(self):
        analysis = self._rule_state_2_window_analysis()
        if analysis is None:
            return None
        return analysis["previous_isp"]["is_regulation_state_2"]

    @property
    def rule_state_2_current_isp_prediction(self):
        analysis = self._rule_state_2_window_analysis()
        if analysis is None:
            return None
        return analysis["current_isp_prediction"]["is_regulation_state_2"]

    @property
    def rule_state_2_analysis(self):
        # Preserve the original fresh-dictionary behavior for callers.
        return deepcopy(self._rule_state_2_window_analysis())

    @property
    def api_last_success(self):
        return self._api_last_success

    @property
    def api_last_failure(self):
        return self._api_last_failure

    @property
    def api_consecutive_auth_failures(self):
        return self._api_consecutive_auth_failures

    @property
    def api_grace_active(self):
        return self._api_consecutive_failures > 0 and self._within_update_grace()

    @property
    def api_response_time_ms(self):
        return self._api_response_time_ms

    @property
    def api_consecutive_failures(self):
        return self._api_consecutive_failures

    @property
    def api_last_error(self):
        return self._api_last_error

    @property
    def api_last_error_details(self):
        return self._api_last_error_details

    @property
    def api_data_delay_seconds(self):
        analysis = self._rule_state_2_window_analysis()
        if analysis is None:
            return None

        latest_interval_end = dt_util.parse_datetime(analysis["latest_interval_end"])
        if latest_interval_end is None:
            return None

        now_local = _as_local_datetime(dt_util.utcnow())
        delay_seconds = int((now_local - _as_local_datetime(latest_interval_end)).total_seconds())
        return max(delay_seconds, 0)

    @property
    def regulation_state_previous_isp(self):
        analysis = self._rule_state_2_window_analysis()
        if analysis is None:
            return None
        return analysis["previous_isp"]["regulation_state"]

    @property
    def regulation_state_current_isp_prediction(self):
        analysis = self._rule_state_2_window_analysis()
        if analysis is None:
            return None
        return analysis["current_isp_prediction"]["regulation_state"]

    @property
    def latest_point(self):
        LOGGER.debug("TennetCoordinator: Accessing latest_point")
        self._ensure_payload_cache()
        if self._cached_latest_point is _CACHE_MISS:
            self._cached_latest_point = self._extract_latest_point(self.data)
        return self._cached_latest_point

    def get_last_known_value(self, key):
        return self._last_known_values.get(key)

    @property
    def keep_last_regulation_prices(self):
        return self._keep_last_regulation_prices

    def _record_failure(self, message, details, *, auth=False):
        """Count failed refreshes, not individual HTTP attempts."""
        self._api_last_failure = dt_util.utcnow()
        self._api_consecutive_failures += 1
        if auth:
            self._api_consecutive_auth_failures += 1
            details = {**details, "consecutive_auth_failures": self._api_consecutive_auth_failures}
        else:
            self._api_consecutive_auth_failures = 0
        self._api_last_error = message
        self._api_last_error_details = details

    def _handle_refresh_failure(self, message):
        """Keep valid data during grace; otherwise signal failure to HA."""
        if self._within_update_grace():
            log = LOGGER.warning if self._api_consecutive_failures == 1 else LOGGER.debug
            log("TenneT refresh failed within grace window, keeping last data: %s", message)
            return self.data
        raise UpdateFailed(message)

    async def _async_update_data(self):
        """Fetch data while preserving last-valid payload and availability semantics."""
        async with self._update_lock:
            # Only coalesce healthy updates. A failed refresh must never turn
            # into a successful coordinator update just by returning cached data.
            if (
                self._last_success_monotonic is not None
                and self.data is not None
                and self.last_update_success
                and self._api_consecutive_failures == 0
                and monotonic() - self._last_success_monotonic < MIN_UPDATE_INTERVAL
            ):
                LOGGER.debug("TenneT: coalescing healthy refresh")
                return self.data

            request_start = monotonic()
            try:
                data = await self.api.get_latest()
            except TennetApiAuthError as err:
                self._record_failure(str(err), err.details, auth=True)
                if (
                    self._api_last_success is None
                    or self._api_consecutive_auth_failures >= AUTH_FAILURE_THRESHOLD
                ):
                    raise ConfigEntryAuthFailed("Invalid API key") from err
                return self._handle_refresh_failure(f"TenneT API auth error (transient): {err}")
            except TennetApiError as err:
                self._record_failure(str(err), err.details)
                return self._handle_refresh_failure(f"TenneT API error: {err}")
            except Exception as err:
                # Avoid forwarding arbitrary exception text that might contain credentials.
                message = f"Unexpected TenneT refresh error: {type(err).__name__}"
                self._record_failure(message, {"type": type(err).__name__, "message": message})
                try:
                    return self._handle_refresh_failure(message)
                except UpdateFailed:
                    raise UpdateFailed(message) from None

            # Preserve the existing optional last-known price behavior.
            if self._keep_last_regulation_prices:
                point = self._extract_latest_point(data)
                if point:
                    for key in REGULATION_PRICE_KEYS:
                        value = point.get(key)
                        if value is None:
                            continue
                        try:
                            self._last_known_values[key] = float(value)
                        except (TypeError, ValueError, OverflowError):
                            continue
            if self._api_consecutive_failures and self.last_update_success:
                LOGGER.info("TenneT API recovered after %s failed refresh(es)", self._api_consecutive_failures)
            now = monotonic()
            self._last_success_monotonic = now
            self._api_last_success = dt_util.utcnow()
            self._api_response_time_ms = int((now - request_start) * 1000)
            self._api_consecutive_failures = 0
            self._api_consecutive_auth_failures = 0
            self._api_last_error = None
            self._api_last_error_details = None
            return data
