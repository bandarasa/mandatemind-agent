import logging
from typing import List, Dict
from .base import BaseCollector
import requests
import xml.etree.ElementTree as ET

logger = logging.getLogger("mandatemind-agent")


class PaloAltoCollector(BaseCollector):
    """
    Collects Palo Alto firewall configuration:
    - Security rules
    - NAT rules
    - Zones
    - Interfaces
    - VPN (GlobalProtect)
    """

    def collect(self) -> List[Dict]:
        logger.info("PaloAltoCollector: starting collection")

        host = self.params["host"]
        username = self.params["username"]
        password = self.params["password"]

        api_key = self._get_api_key(host, username, password)
        if not api_key:
            logger.error("PaloAltoCollector: failed to authenticate (no API key)")
            return [{"error": "Failed to authenticate to Palo Alto"}]

        results = []

        # Security rules
        sec_rules = self._get_config(host, api_key,
            "/config/devices/entry/vsys/entry/rulebase/security")
        results.append({"config_type": "security_rules", "data": sec_rules})

        # NAT rules
        nat_rules = self._get_config(host, api_key,
            "/config/devices/entry/vsys/entry/rulebase/nat")
        results.append({"config_type": "nat_rules", "data": nat_rules})

        # Zones
        zones = self._get_config(host, api_key,
            "/config/devices/entry/network/zones")
        results.append({"config_type": "zones", "data": zones})

        # Interfaces
        interfaces = self._get_config(host, api_key,
            "/config/devices/entry/network/interface")
        results.append({"config_type": "interfaces", "data": interfaces})

        # GlobalProtect VPN
        gp_vpn = self._get_config(host, api_key,
            "/config/devices/entry/vpn")
        results.append({"config_type": "vpn", "data": gp_vpn})

        logger.info(f"PaloAltoCollector: completed successfully with {len(results)} items")
        return results


    # ---------------------------------------------------------
    # Generate API key
    # ---------------------------------------------------------
    def _get_api_key(self, host: str, username: str, password: str) -> str:
        url = f"https://{host}/api/?type=keygen&user={username}&password={password}"
        logger.info("PaloAltoCollector: requesting API key")

        try:
            resp = requests.get(url, verify=False, timeout=10)
            root = ET.fromstring(resp.text)
            key = root.find(".//key")
            if key is None:
                logger.error("PaloAltoCollector: API key not found in response")
                return None
            return key.text
        except Exception as e:
            logger.error(f"PaloAltoCollector: API key request failed: {e}")
            return None


    # ---------------------------------------------------------
    # Generic config pull via XPath
    # ---------------------------------------------------------
    def _get_config(self, host: str, api_key: str, xpath: str) -> Dict:
        url = f"https://{host}/api/?type=config&action=show&xpath={xpath}&key={api_key}"
        logger.info(f"PaloAltoCollector: pulling config for xpath: {xpath}")

        try:
            resp = requests.get(url, verify=False, timeout=15)
            root = ET.fromstring(resp.text)
            return self._xml_to_dict(root)
        except Exception as e:
            logger.error(f"PaloAltoCollector: config pull failed for {xpath}: {e}")
            return {"error": str(e), "xpath": xpath}


    # ---------------------------------------------------------
    # Convert XML to dict
    # ---------------------------------------------------------
    def _xml_to_dict(self, element: ET.Element) -> Dict:
        output = {}
        for child in element:
            if len(child) > 0:
                output[child.tag] = self._xml_to_dict(child)
            else:
                output[child.tag] = child.text
        return output
