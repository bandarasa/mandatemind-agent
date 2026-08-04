import logging
from typing import List, Dict
from .base import BaseCollector
import ldap3

logger = logging.getLogger("mandatemind-agent")


class ADCollector(BaseCollector):
    """
    Collects Active Directory domain-level security policies:
    - Password policy
    - Lockout policy
    - Domain security settings
    """

    def collect(self) -> List[Dict]:
        logger.info("ADCollector: starting LDAP query")

        server_uri = self.params["server"]
        bind_dn = self.params["bind_dn"]
        bind_password = self.params["bind_password"]
        search_base = self.params.get("search_base", "")

        try:
            server = ldap3.Server(server_uri, get_info=ldap3.ALL)
            conn = ldap3.Connection(server, user=bind_dn, password=bind_password, auto_bind=True)
        except Exception as e:
            logger.error(f"ADCollector: failed to bind to LDAP server {server_uri}: {e}")
            return [{"error": str(e)}]

        try:
            conn.search(
                search_base=search_base,
                search_filter="(objectClass=domainDNS)",
                attributes=[
                    "minPwdLength",
                    "pwdHistoryLength",
                    "maxPwdAge",
                    "minPwdAge",
                    "lockoutDuration",
                    "lockoutThreshold",
                    "lockoutObservationWindow",
                    "pwdProperties"
                ],
            )
        except Exception as e:
            logger.error(f"ADCollector: LDAP search failed: {e}")
            conn.unbind()
            return [{"error": str(e)}]

        results = []
        for entry in conn.entries:
            content = {
                "dn": str(entry.entry_dn),
                "minPwdLength": self._safe_int(entry.minPwdLength),
                "pwdHistoryLength": self._safe_int(entry.pwdHistoryLength),
                "maxPwdAge": self._safe_str(entry.maxPwdAge),
                "minPwdAge": self._safe_str(entry.minPwdAge),
                "lockoutDuration": self._safe_str(entry.lockoutDuration),
                "lockoutThreshold": self._safe_int(entry.lockoutThreshold),
                "lockoutObservationWindow": self._safe_str(entry.lockoutObservationWindow),
                "pwdProperties": self._safe_int(entry.pwdProperties),
            }
            results.append(content)

        conn.unbind()

        logger.info(f"ADCollector: completed successfully with {len(results)} items")
        return results

    def _safe_int(self, attr):
        return int(attr.value) if attr and attr.value is not None else None

    def _safe_str(self, attr):
        return str(attr.value) if attr and attr.value is not None else None
