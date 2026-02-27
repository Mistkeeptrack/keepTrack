import os
import requests
from typing import Any, Dict, List, Optional

API_BASE = os.getenv("API_BASE", "http://192.168.1.101:8000")

def get_tasks(user_id: str) -> List[Dict[str, Any]]:
    r = requests.get(f"{API_BASE}/tasks/{user_id}", timeout=10)
    r.raise_for_status()
    return r.json()

def create_task(
    user_id: str,
    title: str,
    description: str = "",
    status: str = "pending",
    priority: str = "medium",
    due_date: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "status": status,
        "priority": priority,
        "due_date": due_date,
    }
    r = requests.post(f"{API_BASE}/tasks", json=payload, timeout=10)
    r.raise_for_status()
    return r.json()