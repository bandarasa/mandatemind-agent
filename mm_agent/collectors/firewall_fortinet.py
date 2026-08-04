import logging
from typing import List, Dict
from .base import BaseCollector
import requests

logger = logging.getLogger("mandatemind-agent")


class FortinetCollector(BaseCollector):
    """
    Collects Fortinet FortiGate firewall configuration:
    - Firewall policies
    - NAT rules
    - Interfaces
    - Zones
    - VPN (IPSec + SSL)
    """

    def collect(self) -> List[Dict]:
        logger.info("FortinetCollector: starting collection")

        host = self.params["host"]
        token = self.params["token"]  # Fortinet uses API token auth

        results = []

        # Firewall policies
        fw_policies = self._get(host, token, "/api/v2/cmdb/firewall/policy")
        results.append({"config_type": "firewall_policies", "data": fw_policies})

        # NAT rules
        nat_rules = self._get(host, token, "/api/v2/cmdb/firewall/ippool")
        results.append({"config_type": "nat_rules", "data": nat_rules})

        # Interfaces
        interfaces = self._get(host, token, "/api/v2/cmdb/system/interface")
        results.append({"config_type": "interfaces", "data": interfaces})

        # Zones
        zones = self._get(host, token, "/api/v2/cmdb/system/zone")
        results.append({"config_type": "zones", "data": zones})

        # IPSec VPN
        ipsec = self._get(host, token, "/api/v2/cmdb/vpn.ipsec/phase1-interface")
        results.append({"config_type": "ipsec_vpn", "data": ipsec})

        # SSL VPN
        sslvpn = self._get(host, token, "/api/v2/cmdb/vpn.ssl/settings")
        results.append({"config_type": "ssl_vpn", "data": sslvpn})

        logger.info(f"FortinetCollector: completed successfully with {len(results)} items")
        return results


    # ---------------------------------------------------------
    # Generic GET wrapper for Fortinet API
    # ---------------------------------------------------------
    def _get(self, host: str, token: str, path: str) -> Dict:
        url = f"https://{host}{path}"
        headers = {
            "Authorization": f"Bearer {token}"
        }

        logger.info(f"FortinetCollector: GET {path}")

        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"FortinetCollector: request failed for {path}: {e}")
            return {"error": str(e), "path": path}
