import requests
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OzonAPIResponse:
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    status_code: int = 200

class OzonSellerAPI:
    def __init__(self, client_id: str, api_key: str):
        self.client_id = str(client_id).strip()
        self.api_key = api_key.strip()
        self.base_url = "https://api-seller.ozon.ru"
        self.session = requests.Session()
        self.session.headers.update({
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        })
    
    def _make_request(self, method: str, endpoint: str, payload: Optional[Dict] = None) -> OzonAPIResponse:
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"API Request: {method} {endpoint}")
            
            if method.upper() == "POST":
                response = self.session.post(url, json=payload, timeout=30)
            else:
                response = self.session.get(url, params=payload, timeout=30)
            
            response.raise_for_status()
            
            if response.status_code == 200:
                return OzonAPIResponse(
                    success=True,
                    data=response.json(),
                    status_code=response.status_code
                )
            else:
                return OzonAPIResponse(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:200]}",
                    status_code=response.status_code
                )
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout при запросе к {endpoint}")
            return OzonAPIResponse(success=False, error="Timeout", status_code=408)
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса: {e}")
            return OzonAPIResponse(success=False, error=str(e), status_code=500)
    
    def get_product_list(self, last_id: str = "", limit: int = 1000) -> OzonAPIResponse:
        endpoint = "/v3/product/list"
        payload = {"filter": {"visibility": "ALL"}, "limit": limit}
        if last_id:
            payload["last_id"] = last_id
        return self._make_request("POST", endpoint, payload)
    
    def get_products_detailed_info(self, product_ids: List[str]) -> OzonAPIResponse:
        endpoint = "/v3/product/info/list"
        payload = {"product_id": product_ids}
        return self._make_request("POST", endpoint, payload)
    
    def get_product_dimensions(self, product_id: str) -> OzonAPIResponse:
        endpoint = "/v4/product/info/attributes"
        payload = {
            "filter": {"product_id": [str(product_id)], "visibility": "ALL"},
            "limit": 1
        }
        return self._make_request("POST", endpoint, payload)

    def get_transaction_list(self, date_from: str, date_to: str, page: int = 1, page_size: int = 1000) -> OzonAPIResponse:
        """Получение списка транзакций за период"""
        endpoint = "/v3/finance/transaction/list"
        payload = {
            "filter": {
                "date": {
                    "from": date_from,
                    "to": date_to
                }
            },
            "page": page,
            "page_size": page_size
        }
        return self._make_request("POST", endpoint, payload)

    def get_postings_fbo_list(self, posting_numbers: List[str], limit: int = 1000) -> OzonAPIResponse:
        """Получение данных отправлений FBO пачкой"""
        endpoint = "/v2/posting/fbo/list"
        payload = {
            "with": {
                "analytics_data": True,
                "financial_data": True
            },
            "filter": {
                "posting_number": posting_numbers
            },
            "limit": limit
        }
        return self._make_request("POST", endpoint, payload)