# TODO: add module docstring, for auto documentation
# TODO: move to pydantic/mgspec models
import requests

from requests.adapters import HTTPAdapter, Retry


class APIClient:
    def __init__(self, timeout: int = 5, max_retries: int = 3):
        self.timeout: int = timeout
        self.max_retries: int = max_retries
        self.session: requests.Session = self._create_session()

    def _create_session(self):
        session = requests.Session()
        retry_strategy = Retry(total=self.max_retries, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def post(self, url, data, headers: dict = None):
        return self.session.post(
            url, data=data, headers=headers, timeout=self.timeout
        )
