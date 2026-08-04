import time
import logging
import os
from typing import Dict, Type
from croniter import croniter
from datetime import datetime

from mm_agent.transport import Transport
from mm_agent.cache import EvidenceCache

logger = logging.getLogger("mandatemind-agent")


class Scheduler:
    def __init__(self, config):
        self.config = config
        self.transport = Transport(
            api_base_url=config.api_base_url,
            api_token=config.api_token,
            tenant_id=config.tenant_id,
            agent_id=config.agent_id,
            signing_key=getattr(config, "signing_key", None),
        )
        self.jobs = {}
        self.cache = EvidenceCache()
        self.last_heartbeat = 0
        self.last_version_check = 0
        self.last_config_sync = 0        # STEP 2.17
        self.last_successful_run = time.time()
        self.collector_failures = {}
        self.last_drift = {}             # STEP 2.18
        self.last_watchdog_tick = time.time()   # STEP 2.23

        # ---------------------------------------------------------
        # STEP 2.26: File Integrity Monitoring (core + collectors)
        # ---------------------------------------------------------
        if os.name == "nt":
            self.agent_base_path = r"C:\Program Files\MandateMind Agent"
        else:
            self.agent_base_path = "/opt/mandatemind-agent"

        self.file_integrity = {}

        critical_files = [
            os.path.join(self.agent_base_path, "mm_agent", "scheduler.py"),
            os.path.join(self.agent_base_path, "mm_agent", "transport.py"),
            os.path.join(self.agent_base_path, "mm_agent", "cache.py"),
            os.path.join(self.agent_base_path, "mm_agent", "version.py"),
            os.path.join(self.agent_base_path, "config.yaml"),
        ]

        for f in critical_files:
            self.file_integrity[f] = self.hash_file(f)

        collectors_dir = os.path.join(self.agent_base_path, "mm_agent", "collectors")
        if os.path.isdir(collectors_dir):
            for root, _, files in os.walk(collectors_dir):
                for fname in files:
                    path = os.path.join(root, fname)
                    self.file_integrity[path] = self.hash_file(path)

        logger.info("Scheduler initialized")

    def register_collector(self, name: str, collector_cls: Type, collector_config):
        cron_expr = self.config.schedule.get(name, "0 * * * *")
        self.jobs[name] = {
            "collector_cls": collector_cls,
            "collector_config": collector_config,
            "cron": cron_expr,
            "next_run": croniter(cron_expr, datetime.utcnow()).get_next(datetime),
        }
        self.collector_failures[name] = 0
        self.last_drift[name] = time.time()   # STEP 2.18
        logger.info(f"Collector registered: {name} (cron: {cron_expr})")

    # ---------------------------------------------------------
    # STEP 2.17: Apply remote config from backend
    # ---------------------------------------------------------
    def apply_remote_config(self, remote: dict):
        logger.info("Scheduler: applying remote configuration")

        # Merge into AgentConfig
        self.config.merge_remote_config(remote)

        # STEP 2.21: Signing key rotation
        if "signing_key" in remote:
            self.config.signing_key = remote["signing_key"]

        # Update transport signing key immediately
        self.transport.signing_key = self.config.signing_key

        # Update collector schedules
        for name, job in self.jobs.items():
            new_cron = self.config.schedule.get(name)
            if new_cron and new_cron != job["cron"]:
                logger.info(f"Scheduler: updating cron for {name} → {new_cron}")
                job["cron"] = new_cron
                job["next_run"] = croniter(new_cron, datetime.utcnow()).get_next(datetime)

        # Enable/disable collectors
        for name, collector_cfg in self.config.collectors.items():
            if name in self.jobs:
                if not collector_cfg.enabled:
                    logger.info(f"Scheduler: disabling collector {name}")
                    self.jobs[name]["disabled"] = True
                else:
                    self.jobs[name]["disabled"] = False

    def run_forever(self):
        logger.info("Scheduler loop started")

        while True:
            now = datetime.utcnow()

            # ---------------------------------------------------------
            # STEP 3: Heartbeat every 60 seconds
            # ---------------------------------------------------------
            if time.time() - self.last_heartbeat > 60:
                self.transport.send_heartbeat(status="healthy")
                self.transport.send_version()
                self.last_heartbeat = time.time()

            # ---------------------------------------------------------
            # STEP 4: Version check every 6 hours
            # ---------------------------------------------------------
            if time.time() - self.last_version_check > 21600:
                version_info = self.transport.check_latest_version()
                self.last_version_check = time.time()

                if version_info:
                    latest = version_info["latest"]
                    minimum = version_info["minimum"]
                    current = version_info["current"]

                    if latest and current and current != latest:
                        logger.warning(f"Agent outdated: current={current}, latest={latest}")

                    if minimum and current and current < minimum:
                        logger.error(
                            f"Agent below minimum supported version: current={current}, minimum={minimum}"
                        )

                    # ---------------------------------------------------------
                    # STEP 2.25: Auto-Apply Update if New Version Available
                    # ---------------------------------------------------------
                    if latest and current and current != latest:
                        logger.warning(f"Scheduler: new agent version available → {latest}")

                        update_path = self.transport.download_update_package(latest)
                        if update_path:
                            logger.info("Scheduler: update package downloaded — applying")
                            self.apply_update_package(update_path)
                        else:
                            logger.error("Scheduler: update download failed")
                            self.transport.send_heartbeat(status="update_failed")

            # ---------------------------------------------------------
            # STEP 2.17: Config sync every 10 minutes
            # ---------------------------------------------------------
            if time.time() - self.last_config_sync > 600:
                logger.info("Scheduler: syncing configuration from backend")
                remote_cfg = self.transport.fetch_config()
                self.last_config_sync = time.time()

                if remote_cfg:
                    self.apply_remote_config(remote_cfg)

            # ---------------------------------------------------------
            # STEP 2.15: Crash Recovery — No successful run in 30 min
            # ---------------------------------------------------------
            if time.time() - self.last_successful_run > 1800:
                logger.error("Scheduler: no successful collector run in 30 minutes")
                self.transport.send_heartbeat(status="error")

            # ---------------------------------------------------------
            # STEP 2.18: Auto-disable collectors with no drift for 24 hours
            # ---------------------------------------------------------
            for cname, job in self.jobs.items():
                if not job.get("disabled"):
                    if time.time() - self.last_drift.get(cname, 0) > 86400:
                        logger.info(f"Scheduler: auto-disabling {cname} due to no drift")
                        job["disabled"] = True

            # ---------------------------------------------------------
            # STEP 2.23: Anti-Tamper Watchdog
            # ---------------------------------------------------------
            now_ts = time.time()
            if now_ts - self.last_watchdog_tick > 120:  # 2 minutes stall
                logger.error("Scheduler: watchdog detected possible tampering or freeze")

                # Send tamper heartbeat
                self.transport.send_heartbeat(status="tamper_detected")

                # Force config sync
                remote_cfg = self.transport.fetch_config()
                if remote_cfg:
                    self.apply_remote_config(remote_cfg)

                # Force reschedule of all collectors
                for name, job in self.jobs.items():
                    job["next_run"] = croniter(job["cron"], datetime.utcnow()).get_next(datetime)
                    logger.info(f"Scheduler: watchdog rescheduled collector {name}")

                # STEP 2.24: Trigger self-restart
                self.restart_agent()

            self.last_watchdog_tick = now_ts

            # ---------------------------------------------------------
            # STEP 2.26: File Integrity Monitoring
            # ---------------------------------------------------------
            for f, baseline_hash in self.file_integrity.items():
                current_hash = self.hash_file(f)
                if current_hash != baseline_hash:
                    logger.error(f"Scheduler: file integrity violation detected → {f}")
                    self.transport.send_heartbeat(status="file_tamper_detected")
                    self.restart_agent()

            # ---------------------------------------------------------
            # Collector execution loop
            # ---------------------------------------------------------
            for name, job in self.jobs.items():
                if job.get("disabled"):
                    logger.info(f"Collector {name} is disabled — skipping")
                    continue

                if now >= job["next_run"]:
                    logger.info(f"Collector due: {name}")
                    self.run_job(name, job)
                    job["next_run"] = croniter(job["cron"], now).get_next(datetime)
                    logger.info(f"Next run for {name}: {job['next_run']}")

            time.sleep(10)

    def run_job(self, name: str, job: Dict):
        logger.info(f"Running collector: {name}")

        collector = job["collector_cls"](
            tenant_id=self.config.tenant_id,
            params=job["collector_config"].params,
        )

        try:
            contents = collector.collect()
            logger.info(f"{name}: collected {len(contents)} items")
            self.collector_failures[name] = 0
        except Exception as e:
            logger.error(f"{name} collector failed: {e}")
            self.collector_failures[name] += 1

            if self.collector_failures[name] >= 3:
                logger.error(f"{name}: collector failed 3 times — escalating")
                self.transport.send_heartbeat(status="error")

            return

        evidence_batch = []

        for content in contents:
            ev = collector.build_evidence(
                source_system=name,
                collector_type=name,
                content=content,
            )

            policy_type = ev["content"]["json"].get("policy_type", "default")
            evidence_key = f"{name}:{policy_type}"

            last_hash = self.cache.get_last_hash(evidence_key)

            if last_hash == ev["hash"]:
                logger.info(f"{name}: no change for {evidence_key}")
                continue

            logger.info(f"{name}: change detected for {evidence_key}")
            self.last_drift[name] = time.time()   # STEP 2.18

            # Auto-enable if previously disabled
            if job.get("disabled"):
                logger.info(f"Scheduler: auto-enabling {name} due to new drift")
                job["disabled"] = False

            self.cache.update_hash(evidence_key, ev["hash"])
            evidence_batch.append(ev)

        if evidence_batch:
            logger.info(f"{name}: uploading {len(evidence_batch)} evidence items")

            try:
                self.transport.send_batch(evidence_batch)
                self.last_successful_run = time.time()
            except Exception as e:
                logger.error(f"{name}: upload failed: {e}")
                self.transport.send_heartbeat(status="error")
        else:
            logger.info(f"{name}: nothing to upload")
            self.last_successful_run = time.time()

    # ---------------------------------------------------------
    # STEP 2.24: Agent Self-Restart
    # ---------------------------------------------------------
    def restart_agent(self):
        logger.error("Scheduler: initiating self-restart (Step 2.24)")

        # Notify backend
        self.transport.send_heartbeat(status="restart")

        # Small delay to flush logs + heartbeat
        time.sleep(2)

        # Exit with code 1 so systemd / service manager restarts agent
        logger.error("Scheduler: exiting process for restart")
        raise SystemExit(1)

    # ---------------------------------------------------------
    # STEP 2.25: Apply Update Package (Hot-Swap)
    # ---------------------------------------------------------
    def apply_update_package(self, update_path: str):
        logger.info(f"Scheduler: applying update package from {update_path}")

        try:
            import zipfile
            with zipfile.ZipFile(update_path, "r") as z:
                z.extractall(self.agent_base_path)

            logger.info("Scheduler: update package applied successfully")

        except Exception as e:
            logger.error(f"Scheduler: failed to apply update package: {e}")
            self.transport.send_heartbeat(status="update_failed")
            return

        # Notify backend
        self.transport.send_heartbeat(status="updated")

        # Restart agent (Step 2.24)
        self.restart_agent()

    # ---------------------------------------------------------
    # STEP 2.26: File hash helper
    # ---------------------------------------------------------
    def hash_file(self, path: str):
        import hashlib
        try:
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None

