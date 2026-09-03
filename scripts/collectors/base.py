from dataclasses import dataclass, field

import requests

UA = "Mozilla/5.0 (compatible; SouthFloridaEventsRadar/2.0; +GitHubActions)"


@dataclass
class CollectorResult:
    events: list[dict] = field(default_factory=list)
    status: str = "ok"
    message: str = ""


class HttpClient:
    def __init__(self, timeout: int = 25):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})

    def get(self, url: str) -> requests.Response:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response
