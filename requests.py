import json as _json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class HTTPErrorException(Exception):
    pass


class Response:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        if not self.text:
            return None
        return _json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPErrorException(f"HTTP {self.status_code}: {self.text}")


def get(url: str, params=None, timeout: int = 20):
    final_url = url
    if params:
        query = urlencode(params)
        connector = "&" if "?" in url else "?"
        final_url = f"{url}{connector}{query}"

    request = Request(final_url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return Response(resp.getcode(), body)
    except HTTPError as err:
        body = err.read().decode("utf-8", errors="ignore")
        return Response(err.code, body)
    except URLError as err:
        raise HTTPErrorException(str(err)) from err
