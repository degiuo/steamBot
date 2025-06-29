import requests
from typing import List, Optional

class ProxyManager:
    def __init__(self, proxy_list: List[str]):
        self.proxies = proxy_list
        self.current_proxy = None

    def get_valid_proxy(self, test_url: str = "https://api.steampowered.com") -> Optional[str]:
        """Находит первый рабочий прокси из списка"""
        for proxy in self.proxies:
            try:
                response = requests.get(
                    test_url,
                    proxies={"http": proxy, "https": proxy},
                    timeout=10
                )
                if response.status_code == 200:
                    self.current_proxy = proxy
                    return proxy
            except:
                continue
        return None

    def rotate_proxy(self) -> Optional[str]:
        """Ротация прокси"""
        if not self.proxies:
            return None
            
        if self.current_proxy in self.proxies:
            index = self.proxies.index(self.current_proxy)
            next_index = (index + 1) % len(self.proxies)
            self.current_proxy = self.proxies[next_index]
        else:
            self.current_proxy = self.proxies[0]
            
        return self.current_proxy