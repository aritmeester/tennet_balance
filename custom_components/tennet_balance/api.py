import aiohttp

class TennetApiClient:
    def __init__(self, api_key: str, environment: str):
        self._api_key = api_key
        self._base_url = f"https://{environment}.tennet.eu"

    async def get_latest(self) -> dict:
        url = f"{self._base_url}/publications/v1/balance-delta-high-res/latest"
        headers = {"Accept": "application/json", "apikey": self._api_key}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as resp:
                resp.raise_for_status()
                return await resp.json()
