import logging
import requests
from typing import List
from mm_agent.version import AGENT_VERSION
import gzip
import json
import hmac
import hashlib   # STEP 2.20
import os
import time

logger = logging.getLogger("mandatemind-agent")


class Transport:
    def __init__(self, api_base_url: str, api_token: str, tenant_id: str, agent_id: str, signing_key: str = None):
        self.api_base_url = api_base_url.rstrip("/")
        self.api_token = api_token
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.signing_key = signing_key   # STEP 2.20

    def send_batch(self, evidence: List[dict]):
        url = f"{self.api_base_url}/api/v1/agent/evidence/batch"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Content-Encoding": "gzip",   # STEP 2.19
        }

        logger.info(f"Transport: preparing batch of {len(evidence)} evidence items")

        # ---------------------------------------------------------
        # STEP 2.19: Deduplication
        # ---------------------------------------------------------
        deduped = {}
        for ev in evidence:
            deduped[ev["hash"]] = ev

        evidence_list = list(deduped.values())
        logger.info(f"Transport: deduplicated batch size: {len(evidence_list)}")

        # ---------------------------------------------------------
        # STEP 2.20: Evidence Signing (HMAC-SHA256)
        # ---------------------------------------------------------
        if self.signing_key:
            for ev in evidence_list:
                ev_hash = ev["hash"].encode("utf-8")
                signature = hmac.new(
                    self.signing_key.encode("utf-8"),
                    ev_hash,
                    hashlib.sha256
                ).hexdigest()
                ev["signature"] = signature

            logger.info("Transport: evidence items signed (HMAC-SHA256)")
        else:
            logger.warning("Transport: no signing key configured — evidence not signed")

        # ---------------------------------------------------------
        # STEP 2.22: Anti-Replay Protection (nonce + timestamp)
        # ---------------------------------------------------------
        timestamp = int(time.time())
        nonce = os.urandom(16).hex()

        # Build canonical string for batch signature
        canonical = f"{timestamp}:{nonce}:" + ",".join(ev["hash"] for ev in evidence_list)

        batch_signature = None
        if self.signing_key:
            batch_signature = hmac.new(
                self.signing_key.encode("utf-8"),
                canonical.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            logger.info("Transport: batch signature generated (HMAC-SHA256)")
        else:
            logger.warning("Transport: no signing key — batch signature omitted")



        # ---------------------------------------------------------
        # STEP 2.19: Compression (gzip)
        # ---------------------------------------------------------
        payload = {
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "timestamp": timestamp,       # STEP 2.22
            "nonce": nonce,               # STEP 2.22
            "batch_signature": batch_signature,  # STEP 2.22
            "evidence": evidence_list,
        }


        raw_json = json.dumps(payload).encode("utf-8")
        compressed = gzip.compress(raw_json)

        logger.info(
            f"Transport: compressed payload size: {len(compressed)} bytes "
            f"(raw: {len(raw_json)} bytes)"
        )

        # ---------------------------------------------------------
        # Send compressed payload
        # ---------------------------------------------------------
        try:
            resp = requests.post(url, data=compressed, headers=headers, timeout=30)
            resp.raise_for_status()
            logger.info("Transport: batch upload successful")
        except Exception as e:
            logger.error(f"Transport: batch upload failed: {e}")
            logger.error(f"Transport: failed payload size (raw): {len(raw_json)}")
            logger.error(f"Transport: failed payload size (compressed): {len(compressed)}")

    # ---------------------------------------------------------
    # Heartbeat / Agent Health
    # ---------------------------------------------------------
    def send_heartbeat(self, status: str = "healthy"):
        url = f"{self.api_base_url}/api/v1/agent/heartbeat"
        payload = {
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "status": status,
        }
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        logger.info(f"Transport: sending heartbeat ({status})")

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            logger.info("Transport: heartbeat acknowledged")
        except Exception as e:
            logger.error(f"Transport: heartbeat failed: {e}")

    # ---------------------------------------------------------
    # Agent Version Reporting
    # ---------------------------------------------------------
    def send_version(self):
        url = f"{self.api_base_url}/api/v1/agent/version"
        payload = {
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "version": AGENT_VERSION,
        }
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        logger.info(f"Transport: reporting agent version {AGENT_VERSION}")

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            logger.info("Transport: version report acknowledged")
        except Exception as e:
            logger.error(f"Transport: version report failed: {e}")

    # ---------------------------------------------------------
    # NEW: Download update package (Step 2.14)
    # ---------------------------------------------------------
    def download_update_package(self, version: str):
        url = f"{self.api_base_url}/api/v1/agent/update/download?version={version}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        logger.info(f"Transport: downloading update package for version {version}")

        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()

            update_path = f"/tmp/mandatemind_agent_update_{version}.zip"
            with open(update_path, "wb") as f:
                f.write(resp.content)

            logger.info(f"Transport: update package saved to {update_path}")
            return update_path

        except Exception as e:
            logger.error(f"Transport: update download failed: {e}")
            return None

    # ---------------------------------------------------------
    # NEW: Check Latest Version (Step 2.13)
    # ---------------------------------------------------------
    def check_latest_version(self):
        url = f"{self.api_base_url}/api/v1/agent/version/latest"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        logger.info("Transport: checking latest agent version")

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            latest = data.get("latest_version")
            minimum = data.get("min_supported_version")

            logger.info(f"Transport: latest={latest}, minimum={minimum}, current={AGENT_VERSION}")

            return {
                "latest": latest,
                "minimum": minimum,
                "current": AGENT_VERSION,
            }

        except Exception as e:
            logger.error(f"Transport: version check failed: {e}")
            return None

    # ---------------------------------------------------------
    # NEW: Fetch remote agent configuration (Step 2.17)
    # ---------------------------------------------------------
    def fetch_config(self):
        url = f"{self.api_base_url}/api/v1/agent/config"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        logger.info("Transport: fetching remote agent configuration")

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            logger.info("Transport: remote configuration received")
            return data

        except Exception as e:
            logger.error(f"Transport: failed to fetch remote config: {e}")
            return None
