#!/usr/bin/env python3
"""Check session 73 tasks and their ticktick IDs"""

import requests
import json

response = requests.get("http://localhost:8000/api/sessions/73")
data = response.json()

print(f"Session 73: {data['description']}")
print(f"Status: {data['status']}")
print(f"Todo count: {data['todo_count']}")
print("\nTasks:")

for i, todo in enumerate(data.get('todos', []), 1):
    print(f"\n{i}. {todo['title']}")
    print(f"   - ticktick_task_id: {todo.get('ticktick_task_id', 'None')}")
    print(f"   - ticktick_project_id: ???")  # Not in response
    print(f"   - ticktick_sync_status: {todo.get('ticktick_sync_status', 'None')}")

print(f"\nTotal tasks: {len(data.get('todos', []))}")
