"""
FastAPI 백엔드 호출 전용 클라이언트
"""
import os
import mimetypes
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


class APIClient:
    """FastAPI 서버 호출 캡슐화"""

    def __init__(self, base_url: str = API_BASE_URL, timeout: int = 600):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/health", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def diagnose(
        self,
        filename: str,
        file_bytes: bytes,
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        CSV/Excel 업로드 + 5대 지표 진단 요청
        weights = {completeness, validity, consistency, accuracy, uniqueness}
        """
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        files = {"file": (filename, file_bytes, content_type)}
        data = {
            "weight_completeness": weights["completeness"],
            "weight_validity":     weights["validity"],
            "weight_consistency":  weights["consistency"],
            "weight_accuracy":     weights["accuracy"],
            "weight_uniqueness":   weights["uniqueness"],
        }
        r = requests.post(
            f"{self.base_url}/api/diagnose",
            files=files, data=data, timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def list_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        r = requests.get(
            f"{self.base_url}/api/history",
            params={"limit": limit}, timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def delete_history(self, diagnosis_id: int) -> bool:
        headers = {}
        if ADMIN_API_KEY:
            headers["X-API-Key"] = ADMIN_API_KEY
        r = requests.delete(
            f"{self.base_url}/api/history/{diagnosis_id}",
            headers=headers,
            timeout=self.timeout,
        )
        return r.status_code == 200


api_client = APIClient()
