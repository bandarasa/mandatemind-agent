import logging
from typing import List, Dict
from .base import BaseCollector

logger = logging.getLogger("mandatemind-agent")

try:
    import winreg
except ImportError:
    winreg = None


class GPOCollector(BaseCollector):
    """
    Collects Windows Group Policy security settings:
    - Password complexity
    - Minimum password length
    - Kerberos policy
    - Audit policy
    - Security options
    """

    def collect(self) -> List[Dict]:
        logger.info("GPOCollector: starting registry collection")

        if winreg is None:
            logger.error("GPOCollector: winreg unavailable (non-Windows environment)")
            return [{
                "error": "GPOCollector requires Windows environment",
                "platform": "non-windows"
            }]

        results = []

        try:
            # -----------------------------
            # Password & Account Policies
            # -----------------------------
            pwd_policy = self._read_registry_values(
                r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
                [
                    "MinimumPasswordLength",
                    "PasswordComplexity",
                    "MaximumPasswordAge",
                    "MinimumPasswordAge",
                    "LockoutDuration",
                    "LockoutThreshold",
                    "ResetLockoutCount"
                ]
            )
            results.append({"policy_type": "password_policy", **pwd_policy})

            # -----------------------------
            # Kerberos Policy
            # -----------------------------
            kerberos_policy = self._read_registry_values(
                r"System\CurrentControlSet\Control\Lsa\Kerberos",
                [
                    "MaxTicketAge",
                    "MaxRenewAge",
                    "MaxServiceAge",
                    "MaxClockSkew"
                ]
            )
            results.append({"policy_type": "kerberos_policy", **kerberos_policy})

            # -----------------------------
            # Audit Policy
            # -----------------------------
            audit_policy = self._read_registry_values(
                r"Software\Policies\Microsoft\Windows\System",
                [
                    "Audit_ForceAuditPolicy",
                    "Audit_AccountLogon",
                    "Audit_Logon",
                    "Audit_ObjectAccess",
                    "Audit_PrivilegeUse",
                    "Audit_ProcessTracking",
                    "Audit_SystemEvents"
                ]
            )
            results.append({"policy_type": "audit_policy", **audit_policy})

            # -----------------------------
            # Security Options
            # -----------------------------
            security_options = self._read_registry_values(
                r"System\CurrentControlSet\Control\Lsa",
                [
                    "LimitBlankPasswordUse",
                    "DisableDomainCreds",
                    "SCENoApplyLegacyAuditPolicy"
                ]
            )
            results.append({"policy_type": "security_options", **security_options})

        except Exception as e:
            logger.error(f"GPOCollector: registry read failed: {e}")
            return [{"error": str(e)}]

        logger.info(f"GPOCollector: completed successfully with {len(results)} items")
        return results

    # ---------------------------------------------------------
    # Helper: Read registry keys safely
    # ---------------------------------------------------------
    def _read_registry_values(self, path: str, keys: List[str]) -> Dict:
        output = {}
        try:
            reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            for key in keys:
                try:
                    value, _ = winreg.QueryValueEx(reg, key)
                    output[key] = value
                except FileNotFoundError:
                    output[key] = None
        except FileNotFoundError:
            logger.warning(f"GPOCollector: registry path not found: {path}")
            output["error"] = f"Registry path not found: {path}"

        return output
