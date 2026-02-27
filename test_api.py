import requests

API_BASE = "http://192.168.1.101:8000"
USER_ID = "f1661323-c5db-4eda-ab4b-0367ebe7252a"

# 1) GET tasks
r = requests.get(f"{API_BASE}/tasks/{USER_ID}", timeout=10)
print("GET /tasks status:", r.status_code)
print("Tasks:", r.json())

# 2) POST new task
payload = {
    "user_id": USER_ID,
    "title": "Task from colleague app",
    "description": "Created via Python client",
    "status": "pending",
    "priority": "medium",
    "due_date": None
}
r = requests.post(f"{API_BASE}/tasks", json=payload, timeout=10)
print("POST /tasks status:", r.status_code)
print("Created:", r.json())

# 3) GET tasks again (confirm it saved)
r = requests.get(f"{API_BASE}/tasks/{USER_ID}", timeout=10)
print("GET /tasks (after) status:", r.status_code)
print("Tasks after:", r.json())



    