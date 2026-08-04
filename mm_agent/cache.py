import json
import hashlib
from pathlib import Path

class EvidenceCache:
    """
    Stores last known hash for each evidence item so unchanged evidence
    is not re-uploaded.
    """

    def __init__(self, path="agent_cache.json"):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
        else:
            self.data = {}

    def get_last_hash(self, evidence_id: str) -> str:
        return self.data.get(evidence_id, {}).get("hash")

    def update_hash(self, evidence_id: str, hash_value: str):
        self.data[evidence_id] = {"hash": hash_value}
        self._save()

    def _save(self):
        self.path.write_text(json.dumps(self.data, indent=2))
