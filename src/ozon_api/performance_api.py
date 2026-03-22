import time
import requests
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PerformanceAPIResponse:
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None

class OzonPerformanceAPI:
    """Клиент для работы с Ozon Performance API (реклама)"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = 0
        self.base_url = "https://api-performance.ozon.ru/api/client"
        
    def _get_token(self) -> Optional[str]:
        """Получение или обновление токена"""
        current_time = time.time()
        
        # Если токен еще действителен (меньше 30 минут)
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token
            
        url = f"{self.base_url}/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if "access_token" in data:
                self.access_token = data["access_token"]
                # Токен действителен 30 минут (1800 секунд), берем с запасом
                self.token_expires_at = current_time + 1700
                return self.access_token
            else:
                logger.error("Не удалось получить токен: %s", data)
                return None
                
        except Exception as e:
            logger.error("Ошибка при получении токена: %s", str(e))
            return None
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> PerformanceAPIResponse:
        """Выполнение запроса к API"""
        token = self._get_token()
        if not token:
            return PerformanceAPIResponse(
                success=False, 
                error="Не удалось получить токен"
            )
            
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            
            if response.status_code == 200:
                return PerformanceAPIResponse(
                    success=True,
                    data=response.json()
                )
            elif response.status_code == 204:
                return PerformanceAPIResponse(success=True, data=None)
            else:
                return PerformanceAPIResponse(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            return PerformanceAPIResponse(
                success=False,
                error=str(e)
            )
    
    def get_campaigns(self) -> PerformanceAPIResponse:
        """Получение списка кампаний"""
        return self._make_request("GET", "campaign")
    
    def request_statistics_report(self, campaigns: List[str], date_from: str, date_to: str) -> PerformanceAPIResponse:
        """Запрос отчета по статистике"""
        payload = {
            "campaigns": campaigns,
            "from": date_from,
            "to": date_to,
            "groupBy": "DATE"
        }
        return self._make_request("POST", "statistics/json", json=payload)
    
    def get_report_status(self, uuid: str) -> PerformanceAPIResponse:
        """Проверка статуса отчета"""
        return self._make_request("GET", f"statistics/report?UUID={uuid}")