from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime
import uuid
import hashlib
import json

class BaseCollector(ABC):
    def __init__(self, tenant_id: str, params: Dict):
        self.tenant_id = tenant_id
        self.params = params

    @abstractmethod
    def collect(self) -> List[Dict]:
        """
        Return a list of normalized evidence content dicts.
        """
        pass

    def build_evidence(self, source_system: str, collector_type: str, content: Dict) -> Dict:
        raw_json = json.dumps(content, sort_keys=True)
        hash_value = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

        return {
            "tenant_id": self.tenant_id,
            "source_system": source_system,
            "collector_type": collector_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "evidence_id": str(uuid.uuid4()),
            "hash": hash_value,
            "version_parent_id": None,
            "content": {
                "raw": None,
                "json": content,
                "files": []
            },
            "tags": []
        }
