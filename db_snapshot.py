# db_snapshot.py
"""Snapshot and restore in-memory database state for debugging."""

import json
import os
from datetime import datetime
from typing import Optional

from database import db
from db_config import DatabaseConfig
from models import (
    Alias,
    CID,
    EntityInteraction,
    Export,
    PageView,
    Secret,
    Server,
    ServerInvocation,
    Variable,
)


class DatabaseSnapshot:
    """Manages snapshots of in-memory database state."""

    SNAPSHOT_DIR = "snapshots"

    @classmethod
    def create_snapshot(cls, name: Optional[str] = None) -> str:
        """
        Create a snapshot of the current in-memory database state.

        Returns the path to the snapshot file.

        Raises:
            RuntimeError: If not in memory mode
        """
        if not DatabaseConfig.is_memory_mode():
            raise RuntimeError("Snapshots are only supported in memory mode")

        if name is None:
            name = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        os.makedirs(cls.SNAPSHOT_DIR, exist_ok=True)
        snapshot_path = os.path.join(cls.SNAPSHOT_DIR, f"{name}.json")

        snapshot_data = {"created_at": datetime.utcnow().isoformat(), "tables": {}}

        # Export each model's data
        models = [
            ("servers", Server),
            ("aliases", Alias),
            ("variables", Variable),
            ("secrets", Secret),
            ("page_views", PageView),
            ("entity_interactions", EntityInteraction),
            ("server_invocations", ServerInvocation),
            ("exports", Export),
        ]

        for table_name, model in models:
            records = []
            for record in model.query.all():
                record_dict = {
                    c.name: getattr(record, c.name)
                    for c in record.__table__.columns
                    if c.name != "id"
                }
                # Handle datetime serialization
                for key, value in record_dict.items():
                    if hasattr(value, "isoformat"):
                        record_dict[key] = value.isoformat()
                    elif isinstance(value, bytes):
                        record_dict[key] = value.hex()
                records.append(record_dict)
            snapshot_data["tables"][table_name] = records

        # Handle CIDs separately due to binary data
        cid_records = []
        for cid in CID.query.all():
            cid_records.append(
                {
                    "path": cid.path,
                    "file_data": cid.file_data.hex() if cid.file_data else None,
                    "file_size": cid.file_size,
                    "created_at": (
                        cid.created_at.isoformat() if cid.created_at else None
                    ),
                }
            )
        snapshot_data["tables"]["cids"] = cid_records

        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f, indent=2)

        return snapshot_path

    @classmethod
    def list_snapshots(cls) -> list[str]:
        """List all available snapshots."""
        if not os.path.exists(cls.SNAPSHOT_DIR):
            return []
        return sorted(
            [f[:-5] for f in os.listdir(cls.SNAPSHOT_DIR) if f.endswith(".json")]
        )

    @classmethod
    def delete_snapshot(cls, name: str) -> bool:
        """Delete a snapshot by name."""
        snapshot_path = os.path.join(cls.SNAPSHOT_DIR, f"{name}.json")
        if os.path.exists(snapshot_path):
            os.remove(snapshot_path)
            return True
        return False

    @classmethod
    def get_snapshot_info(cls, name: str) -> Optional[dict]:
        """Get information about a snapshot."""
        snapshot_path = os.path.join(cls.SNAPSHOT_DIR, f"{name}.json")
        if not os.path.exists(snapshot_path):
            return None

        with open(snapshot_path, "r") as f:
            data = json.load(f)

        info = {
            "name": name,
            "created_at": data.get("created_at"),
            "tables": {},
        }

        for table_name, records in data.get("tables", {}).items():
            info["tables"][table_name] = len(records)

        return info
