"""API client for Brand Intel backend"""
import requests
from typing import Optional, Dict, Any, List
from config import API_BASE_URL


class BrandIntelAPI:
    """API client wrapper for all Brand Intel endpoints"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        try:
            response = self.session.get(f"{self.base_url}{endpoint}", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def _post(self, endpoint: str, json: Optional[Dict] = None) -> Any:
        try:
            response = self.session.post(f"{self.base_url}{endpoint}", json=json, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def _put(self, endpoint: str, json: Optional[Dict] = None) -> Any:
        try:
            response = self.session.put(f"{self.base_url}{endpoint}", json=json, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def _delete(self, endpoint: str) -> Any:
        try:
            response = self.session.delete(f"{self.base_url}{endpoint}", timeout=10)
            response.raise_for_status()
            return response.json() if response.content else {"status": "deleted"}
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def _patch(self, endpoint: str, json: Optional[Dict] = None) -> Any:
        try:
            response = self.session.patch(f"{self.base_url}{endpoint}", json=json, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_health(self) -> Dict:
        return self._get("/health")
    
    def get_detailed_health(self) -> Dict:
        return self._get("/health/detailed")
    
    def get_metrics(self) -> Dict:
        return self._get("/health/metrics")
    
    def list_brands(self, active_only: bool = False) -> List[Dict]:
        return self._get("/brands", params={"active_only": active_only})
    
    def get_brand(self, brand_id: str) -> Dict:
        return self._get(f"/brands/{brand_id}")
    
    def create_brand(self, brand_data: Dict) -> Dict:
        return self._post("/brands", json=brand_data)
    
    def update_brand(self, brand_id: str, brand_data: Dict) -> Dict:
        return self._put(f"/brands/{brand_id}", json=brand_data)
    
    def delete_brand(self, brand_id: str) -> Dict:
        return self._delete(f"/brands/{brand_id}")
    
    def toggle_brand(self, brand_id: str) -> Dict:
        return self._patch(f"/brands/{brand_id}/toggle")
    
    def get_monitor_status(self) -> Dict:
        return self._get("/monitors/status")
    
    def trigger_all_monitors(self, brand_id: Optional[str] = None) -> Dict:
        json_data = {"brand_id": brand_id} if brand_id else {}
        return self._post("/monitors/trigger", json=json_data)
    
    def trigger_monitor(self, monitor_type: str, brand_id: str) -> Dict:
        return self._post(f"/monitors/{monitor_type}/trigger", json={"brand_id": brand_id})
    
    def get_monitor_runs(self, limit: int = 50, status: Optional[str] = None, 
                        monitor_type: Optional[str] = None, brand_id: Optional[str] = None) -> List[Dict]:
        params = {"limit": limit}
        if status:
            params["status"] = status
        if monitor_type:
            params["monitor_type"] = monitor_type
        if brand_id:
            params["brand_id"] = brand_id
        return self._get("/monitors/runs", params=params)
    
    def get_monitor_health(self, monitor_type: str) -> Dict:
        return self._get(f"/monitors/{monitor_type}/health")
    
    def list_hits(self, brand_id: Optional[str] = None, status: Optional[str] = None,
                 source: Optional[str] = None, limit: int = 50, page: int = 1) -> Dict:
        params = {"limit": limit, "page": page}
        if brand_id:
            params["brand_id"] = brand_id
        if status:
            params["status"] = status
        if source:
            params["source"] = source
        return self._get("/hits", params=params)
    
    def get_hit(self, hit_id: str) -> Dict:
        return self._get(f"/hits/{hit_id}")
    
    def update_hit_status(self, hit_id: str, status: str, notes: Optional[str] = None) -> Dict:
        json_data = {"status": status}
        if notes:
            json_data["notes"] = notes
        return self._patch(f"/hits/{hit_id}/status", json=json_data)
    
    def get_hits_stats(self, brand_id: Optional[str] = None, days: int = 7) -> Dict:
        params = {"days": days}
        if brand_id:
            params["brand_id"] = brand_id
        return self._get("/hits/stats", params=params)
    
    def get_enrichment_config(self) -> Dict:
        return self._get("/enrichment/config")
    
    def update_enrichment_config(self, config: Dict) -> Dict:
        return self._put("/enrichment/config", json=config)
    
    def get_enrichment_stats(self) -> Dict:
        return self._get("/enrichment/stats")
    
    def process_hit(self, hit_id: str) -> Dict:
        return self._post(f"/enrichment/process/{hit_id}")
    
    def get_dlq_items(self, limit: int = 50) -> List[Dict]:
        return self._get("/admin/dlq", params={"limit": limit})
    
    def retry_dlq_item(self, item_id: str) -> Dict:
        return self._post(f"/admin/dlq/{item_id}/retry")
    
    def delete_dlq_item(self, item_id: str) -> Dict:
        return self._delete(f"/admin/dlq/{item_id}")
    
    def reset_circuit_breaker(self, monitor_type: str) -> Dict:
        return self._post("/admin/circuit-breaker/reset", json={"monitor_type": monitor_type})
    
    def trigger_cleanup(self) -> Dict:
        return self._post("/admin/cleanup")
