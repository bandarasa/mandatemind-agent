import logging
from typing import List, Dict
from .base import BaseCollector
import requests
import time

logger = logging.getLogger("mandatemind-agent")


class IntuneCollector(BaseCollector):
    """
    Collects endpoint posture from Microsoft Intune:
    - Compliance status
    - Encryption
    - OS version
    - Patch level
    - EDR/AV status
    """

    def collect(self) -> List[Dict]:
        logger.info("IntuneCollector: starting collection")

        tenant_id = self.params["tenant_id"]
        client_id = self.params["client_id"]
        client_secret = self.params["client_secret"]

        token = self._get_token(tenant_id, client_id, client_secret)
        if not token:
            logger.error("IntuneCollector: failed to authenticate (no token)")
            return [{"error": "Failed to authenticate to Intune"}]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        results = []

        # Managed devices
        devices = self._get(
            "https://graph.microsoft.com/beta/deviceManagement/managedDevices",
            headers
        )
        results.append({"config_type": "managed_devices", "data": devices})

        # Compliance policies
        compliance = self._get(
            "https://graph.microsoft.com/beta/deviceManagement/deviceCompliancePolicies",
            headers
        )
        results.append({"config_type": "compliance_policies", "data": compliance})

        # Device compliance statuses
        compliance_status = self._get(
            "https://graph.microsoft.com/beta/deviceManagement/deviceCompliancePolicySettingStateSummaries",
            headers
        )
        results.append({"config_type": "compliance_status", "data": compliance_status})

        logger.info(f"IntuneCollector: completed successfully with {len(results)} items")
        return results


    # ---------------------------------------------------------
    # OAuth2 token retrieval
    # ---------------------------------------------------------
    def _get_token(self, tenant_id: str, client_id: str, client_secret: str) -> str:
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }

        logger.info("IntuneCollector: requesting OAuth2 token")

        try:
            resp = requests.post(url, data=data, timeout=15)
            resp.raise_for_status()
            token = resp.json().get("access_token")
            if not token:
                logger.error("IntuneCollector: token missing in response")
            return token
        except Exception as e:
            logger.error(f"IntuneCollector: token request failed: {e}")
            return None


    # ---------------------------------------------------------
    # Generic GET wrapper
    # ---------------------------------------------------------
    def _get(self, url: str, headers: Dict) -> Dict:
        logger.info(f"IntuneCollector: GET {url}")

        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"IntuneCollector: GET failed for {url}: {e}")
            return {"error": str(e), "url": url}
