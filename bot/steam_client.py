import requests
from steampy.client import SteamClient
from steampy.exceptions import InvalidCredentials, ApiException
from .exceptions import TradeOfferError, InventoryError, ProxyError

class SteamClientWrapper:
    def __init__(self, api_key: str, username: str, password: str, ma_file_path: str, proxy: str = None):
        self.client = SteamClient(api_key)
        self.proxy = proxy
        self._setup_session()
        self._login(username, password, ma_file_path)

    def _setup_session(self):
        if self.proxy:
            proxies = {"http": self.proxy, "https": self.proxy}
            self.client.session.proxies.update(proxies)
            try:
                # Проверка работоспособности прокси
                test = requests.get("https://api.steampowered.com", proxies=proxies, timeout=10)
                if test.status_code != 200:
                    raise ProxyError("Proxy test failed")
            except Exception as e:
                raise ProxyError(f"Proxy error: {e}")

    def cancel_trade_offer(self, offer_id: str) -> bool:
        try:
            response = self.client._session.post(
                "https://steamcommunity.com/tradeoffer/" + offer_id + "/cancel",
                data={"sessionid": self.client._get_session_id()},
                timeout=15
            )
            return response.json().get('success', 0) == 1
        except Exception as e:
            raise TradeOfferError(f"Cancel offer error: {e}")

    def _login(self, username: str, password: str, ma_file_path: str):
        try:
            self.client.login(username, password, ma_file_path)
        except InvalidCredentials as e:
            raise TradeOfferError(f"Steam auth failed: {e}")

    def get_trade_offers(self) -> list:
        try:
            return self.client.get_trade_offers()
        except ApiException as e:
            raise TradeOfferError(f"Failed to get offers: {e}")

    def send_trade_offer(self, partner_steam_id: str, items_to_send: list, message: str = "") -> str:
        try:
            return self.client.make_offer(items_to_send, [], partner_steam_id, message)
        except ApiException as e:
            raise TradeOfferError(f"Offer failed: {e}")

    def get_inventory(self, app_id: int) -> list:
        try:
            return self.client.get_my_inventory(game=app_id)
        except ApiException as e:
            raise InventoryError(f"Inventory error: {e}")