import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional

THREADS_FILE = os.path.join(os.path.dirname(__file__), "data", "threads.json")

def _ensure_data_dir():
    os.makedirs(os.path.dirname(THREADS_FILE), exist_ok=True)

def _load_all() -> Dict[str, dict]:
    if not os.path.exists(THREADS_FILE):
        return {}
    try:
        with open(THREADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def _save_all(threads: Dict[str, dict]):
    _ensure_data_dir()
    with open(THREADS_FILE, "w", encoding="utf-8") as f:
        json.dump(threads, f, indent=2, ensure_ascii=False)

def create_thread(title: str = "New Chat") -> str:
    thread_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    threads = _load_all()
    threads[thread_id] = {
        "thread_id": thread_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": []
    }
    _save_all(threads)
    return thread_id

def get_thread(thread_id: str) -> Optional[dict]:
    return _load_all().get(thread_id)

def list_threads() -> List[dict]:
    threads = _load_all()
    # Sort by updated_at descending
    return sorted(threads.values(), key=lambda x: x["updated_at"], reverse=True)

def add_message(thread_id: str, role: str, content: str):
    threads = _load_all()
    if thread_id not in threads:
        return
    
    now = datetime.now().isoformat()
    message = {
        "role": role,
        "content": content,
        "timestamp": now
    }
    
    threads[thread_id]["messages"].append(message)
    threads[thread_id]["updated_at"] = now
    
    # Update title if it's the first user message
    if role == "user" and (threads[thread_id]["title"] == "New Chat" or len(threads[thread_id]["messages"]) <= 1):
        # Use first 30 chars of message as title
        title = content[:30] + "..." if len(content) > 30 else content
        threads[thread_id]["title"] = title
        
    _save_all(threads)

def delete_thread(thread_id: str):
    threads = _load_all()
    if thread_id in threads:
        del threads[thread_id]
        _save_all(threads)
