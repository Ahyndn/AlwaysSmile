import requests


class APIError(Exception):
    """Raised when the external product API cannot provide valid data."""


class DummyJSONProductClient:
    """Retrieves and validates product data from the DummyJSON API."""

    API_BASE_URL = "https://dummyjson.com/products"
    DEFAULT_PAGE_SIZE = 100
    DEFAULT_TIMEOUT = 15

    HEADERS = {
        "Accept": "application/json",
        "User-Agent": "AlwaysSmile/1.0",
    }

    def __init__(
        self,
        session=None,
        base_url=None,
        page_size=DEFAULT_PAGE_SIZE,
        timeout=DEFAULT_TIMEOUT,
    ):
        if (
            not isinstance(page_size, int)
            or isinstance(page_size, bool)
            or page_size < 1
        ):
            raise ValueError("Page size must be a positive integer.")

        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or timeout <= 0
        ):
            raise ValueError("Timeout must be greater than zero.")

        self.session = session if session is not None else requests.Session()

        self.base_url = (base_url or self.API_BASE_URL).rstrip("/")

        self.page_size = page_size
        self.timeout = timeout

    def fetch_products(self):
        """Retrieve every available product through API pagination."""

        products = []
        skip = 0
        total = None

        while total is None or skip < total:
            params = {
                "limit": self.page_size,
                "skip": skip,
            }

            try:
                response = self.session.get(
                    self.base_url,
                    params=params,
                    headers=self.HEADERS,
                    timeout=self.timeout,
                )

                response.raise_for_status()
                payload = response.json()

            except ValueError as error:
                raise APIError("The product API returned invalid JSON.") from error

            except requests.RequestException as error:
                raise APIError(
                    "Unable to retrieve product data from DummyJSON."
                ) from error

            if not isinstance(payload, dict):
                raise APIError(
                    "The product API returned an invalid response structure."
                )

            page = payload.get("products")

            if not isinstance(page, list):
                raise APIError(
                    "The product API response does not contain a valid products list."
                )

            if not all(isinstance(product, dict) for product in page):
                raise APIError("The product API returned an invalid product record.")

            if total is None:
                total = payload.get("total", len(page))

                if not isinstance(total, int) or isinstance(total, bool) or total < 0:
                    raise APIError("The product API returned an invalid product count.")

            if not page:
                if skip < total:
                    raise APIError(
                        "The product API returned incomplete inventory data."
                    )

                break

            if len(page) > self.page_size:
                raise APIError("The product API returned an oversized page.")

            products.extend(page)
            skip += len(page)

        return products


def fetch_products():
    """
    Backward-compatible interface for existing Django views.
    """

    client = DummyJSONProductClient()

    return client.fetch_products()
