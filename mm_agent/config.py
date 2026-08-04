import yaml
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class CollectorConfig:
    enabled: bool
    params: dict

@dataclass
class AgentConfig:
    tenant_id: str
    agent_id: str
    api_base_url: str
    api_token: str
    schedule: dict
    collectors: dict

    # ---------------------------------------------------------
    # Step 2.17: Merge backend config into local config
    # ---------------------------------------------------------
    def merge_remote_config(self, remote: dict):
        # Update schedule
        if "schedule" in remote:
            self.schedule.update(remote["schedule"])

        # Update collectors
        if "collectors" in remote:
            for name, cfg in remote["collectors"].items():
                if name in self.collectors:
                    self.collectors[name].enabled = cfg.get("enabled", self.collectors[name].enabled)

                    # Update params
                    for k, v in cfg.items():
                        if k != "enabled":
                            self.collectors[name].params[k] = v

        # Update other dynamic params
        if "params" in remote:
            for k, v in remote["params"].items():
                setattr(self, k, v)


def load_config(path: str = "config.yaml") -> AgentConfig:
    data = yaml.safe_load(Path(path).read_text())

    collectors = {}
    for name, cfg in data.get("collectors", {}).items():
        collectors[name] = CollectorConfig(
            enabled=cfg.get("enabled", False),
            params={k: v for k, v in cfg.items() if k != "enabled"}
        )

    return AgentConfig(
        tenant_id=data["tenant_id"],
        agent_id=data["agent_id"],
        api_base_url=data["api_base_url"],
        api_token=data["api_token"],
        schedule=data.get("schedule", {}),
        collectors=collectors,
    )
