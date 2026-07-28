#!/usr/bin/env python3
"""
wardkeeper.py — WARDKEEPER Vikunja Backend

Manages project trees via Vikunja REST API. Same CLI interface as the MD-FILES
version but writes to MariaDB via Vikunja instead of a local JSON file.

Usage:
  wardkeeper.py                                        # status check: what's missing?
  wardkeeper.py init                                   # create root project + 5 subprojects
  wardkeeper.py migrate [--dry-run]                    # import from MD-FILES/data/projects.json

  wardkeeper.py navigate [id]                          # navigation menu at given level
  wardkeeper.py list [--json]                          # show full tree
  wardkeeper.py subtasks [--open] [--json]            # list subtasks

  wardkeeper.py add project --name NAME
  wardkeeper.py add epic    --project ID --name NAME [NAME2 ...] [--vibe VIBE]
  wardkeeper.py add story   --epic ID    --name NAME [NAME2 ...]
  wardkeeper.py add task    --story ID   --name NAME [NAME2 ...]
  wardkeeper.py add subtask --task ID    --text TEXT [TEXT2 ...]

  wardkeeper.py set subtask ID [--date YYYY-MM-DD] [--done] [--text TEXT]
  wardkeeper.py done task  ID
  wardkeeper.py done story ID
  wardkeeper.py delete ID
"""

import json
import sys
import argparse
import re
import configparser
from pathlib import Path
from dataclasses import dataclass, field

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests

# ─── Config ──────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "wardkeeper.cfg"

SUBPROJECTS = ["workflow", "inspirator", "belief_agent", "operator", "additionals"]

# Depth in workflow project determines type
DEPTH_NAMES = {0: "epic", 1: "story", 2: "task", 3: "subtask"}
DEPTH_EMOJI = {0: "🎯", 1: "🏁", 2: "⚡", 3: "⬜"}


def load_config():
    if not CONFIG_FILE.exists():
        print("ERROR: wardkeeper.cfg not found. Run 'wardkeeper.py init' or create it manually.")
        sys.exit(1)
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE, encoding="utf-8")
    section = cfg["vikunja"]

    # Load token from .vikunjaenv file
    token_file = BASE_DIR / ".vikunjaenv"
    if token_file.exists():
        section["token"] = token_file.read_text(encoding="utf-8").strip()
    elif "token" not in section:
        print("ERROR: No token found. Create .vikunjaenv with your Vikunja API token.")
        sys.exit(1)

    return section


def save_root_id(root_id):
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE, encoding="utf-8")
    cfg["vikunja"]["root_id"] = str(root_id)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)


# ─── Description markers ────────────────────────────────────────────────────

def build_description(body="", parent_id=None, flags=None, date=None):
    parts = []
    if body:
        parts.append(body)
    markers = []
    if parent_id is not None:
        markers.append(f"<!-- wk:parent:{parent_id} -->")
    if flags:
        for flag in flags:
            markers.append(f"<!-- wk:{flag} -->")
    if date:
        markers.append(f"<!-- wk:date:{date} -->")
    if markers:
        parts.append("\n".join(markers))
    return "\n\n".join(parts)


def parse_description(desc):
    if not desc:
        return {"body": "", "parent_id": None, "flags": set(), "date": None}
    parent = re.search(r"<!-- wk:parent:(\d+) -->", desc)
    date = re.search(r"<!-- wk:date:([\d-]+) -->", desc)
    flags = set(re.findall(r"<!-- wk:(no_tasks|no_subtasks) -->", desc))
    body = re.sub(r"\s*<!-- wk:[^>]+ -->\s*", "", desc).strip()
    return {
        "body": body,
        "parent_id": int(parent.group(1)) if parent else None,
        "flags": flags,
        "date": date.group(1) if date else None,
    }


# ─── Vikunja Client ─────────────────────────────────────────────────────────

class VikunjaClient:
    def __init__(self, url, token):
        self.url = url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["Content-Type"] = "application/json"

    def _req(self, method, path, json_data=None):
        url = f"{self.url}/api/v1{path}"
        r = self.session.request(method, url, json=json_data)
        if r.status_code == 204:
            return None
        if r.status_code >= 400:
            print(f"ERROR: Vikunja API {method} {path} → {r.status_code}: {r.text[:200]}")
            sys.exit(1)
        if not r.text:
            return None
        return r.json()

    def _get_all_pages(self, path):
        page, results = 1, []
        while True:
            sep = "&" if "?" in path else "?"
            batch = self._req("GET", f"{path}{sep}page={page}&per_page=50")
            if not batch:
                break
            results.extend(batch)
            if len(batch) < 50:
                break
            page += 1
        return results

    # --- projects ---

    def list_child_projects(self, parent_id):
        all_projects = self._get_all_pages("/projects")
        return [p for p in all_projects if p.get("parent_project_id") == parent_id]

    def create_project(self, title, parent_id=0):
        return self._req("PUT", "/projects", {
            "title": title,
            "parent_project_id": parent_id,
        })

    def delete_project(self, project_id):
        self._req("DELETE", f"/projects/{project_id}")

    def get_project(self, project_id):
        return self._req("GET", f"/projects/{project_id}")

    def try_get_project(self, project_id):
        """Get project, return None on 404 instead of exiting."""
        url = f"{self.url}/api/v1/projects/{project_id}"
        r = self.session.get(url)
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            return None
        return r.json()

    # --- tasks ---

    def get_project_tasks(self, project_id):
        # First get the default view
        views = self._req("GET", f"/projects/{project_id}/views")
        if not views:
            return []
        view_id = views[0]["id"]
        return self._get_all_pages(f"/projects/{project_id}/views/{view_id}/tasks")

    def get_task(self, task_id):
        return self._req("GET", f"/tasks/{task_id}")

    def create_task(self, project_id, title, description=""):
        return self._req("PUT", f"/projects/{project_id}/tasks", {
            "title": title,
            "description": description,
        })

    def update_task(self, task_id, **fields):
        return self._req("POST", f"/tasks/{task_id}", fields)

    def delete_task(self, task_id):
        self._req("DELETE", f"/tasks/{task_id}")

    # --- relations ---

    def create_relation(self, parent_task_id, child_task_id):
        self._req("PUT", f"/tasks/{parent_task_id}/relations", {
            "other_task_id": child_task_id,
            "relation_kind": "subtask",
        })

    # --- comments ---

    def add_comment(self, task_id, comment):
        self._req("PUT", f"/tasks/{task_id}/comments", {
            "comment": comment,
        })


# ─── Tree Model ──────────────────────────────────────────────────────────────

@dataclass
class WKNode:
    id: int
    title: str
    depth: int = 0
    done: bool = False
    parent_id: int = 0
    flags: set = field(default_factory=set)
    date: str = None
    vibe: str = ""
    children: list = field(default_factory=list)

    @property
    def type_name(self):
        return DEPTH_NAMES.get(self.depth, "item")

    @property
    def emoji(self):
        if self.depth == 3:
            return "✅" if self.done else "⬜"
        return DEPTH_EMOJI.get(self.depth, "📄")


def _parse_due_date(due_date):
    """Parse Vikunja due_date, returning None for empty/zero dates."""
    if not due_date:
        return None
    d = due_date[:10]
    if d.startswith("0001"):
        return None
    return d


def build_tree(tasks):
    """Build tree from flat task list using description parent markers."""
    nodes = {}
    for t in tasks:
        parsed = parse_description(t.get("description", ""))
        nodes[t["id"]] = WKNode(
            id=t["id"],
            title=t["title"],
            done=t.get("done", False),
            parent_id=parsed["parent_id"],
            flags=parsed["flags"],
            date=parsed["date"] or _parse_due_date(t.get("due_date")),
            vibe=parsed["body"],
        )

    roots = []
    for node in nodes.values():
        if node.parent_id and node.parent_id in nodes:
            nodes[node.parent_id].children.append(node)
        elif node.parent_id is None:
            roots.append(node)
        else:
            # parent_id points to project, not another task → root level
            roots.append(node)

    # Sort children by id (creation order) and assign depths
    def assign_depth(node, depth):
        node.depth = depth
        node.children.sort(key=lambda c: c.id)
        for child in node.children:
            assign_depth(child, depth + 1)

    roots.sort(key=lambda n: n.id)
    for root in roots:
        assign_depth(root, 0)

    return roots


def collect_subtasks(node):
    """Collect all subtask-level (depth 3) nodes from tree."""
    result = []
    if node.depth == 3:
        result.append(node)
    for child in node.children:
        result.extend(collect_subtasks(child))
    return result


def collect_all_descendants(node):
    """DFS collect all descendant IDs including self."""
    ids = [node.id]
    for child in node.children:
        ids.extend(collect_all_descendants(child))
    return ids


def find_node(roots, node_id):
    """Find a node by ID in the tree."""
    for root in roots:
        if root.id == node_id:
            return root
        found = _find_in(root, node_id)
        if found:
            return found
    return None


def _find_in(node, node_id):
    for child in node.children:
        if child.id == node_id:
            return child
        found = _find_in(child, node_id)
        if found:
            return found
    return None


# ─── Display ─────────────────────────────────────────────────────────────────

def display_tree(client, root_id, json_out=False):
    workflow_projects = get_workflow_projects(client, root_id)
    if not workflow_projects:
        print("  (no projects)")
        return

    if json_out:
        all_data = []
        for wp in workflow_projects:
            tasks = client.get_project_tasks(wp["id"])
            all_data.append({"project": wp, "tasks": tasks})
        print(json.dumps(all_data, indent=2, ensure_ascii=False))
        return

    for wp in workflow_projects:
        tasks = client.get_project_tasks(wp["id"])
        tree = build_tree(tasks)
        open_st = sum(1 for root in tree for s in collect_subtasks(root) if not s.done)
        print(f"\n📁  {wp['title']}  (id={wp['id']})  [{open_st} open subtasks]")
        for epic in tree:
            _print_node(epic, "  ")


def _print_node(node, indent):
    if node.depth == 3:
        date_str = f"  [{node.date}]" if node.date else "  [open]"
        print(f"{indent}{node.id}. {node.emoji} {node.title}{date_str}")
    else:
        extra = ""
        if node.vibe and node.depth == 0:
            extra = f"  Vibe: {node.vibe[:60]}"
        child_count = len(node.children)
        child_type = DEPTH_NAMES.get(node.depth + 1, "items")
        print(f"{indent}{node.id}. {node.emoji}  {node.title}  [{child_count} {child_type}s]{extra}")
        for child in node.children:
            _print_node(child, indent + "   ")


def display_subtasks(client, root_id, open_only=False, json_out=False):
    workflow_projects = get_workflow_projects(client, root_id)
    result = []
    for wp in workflow_projects:
        tasks = client.get_project_tasks(wp["id"])
        tree = build_tree(tasks)
        for epic in tree:
            _collect_subtasks_with_path(epic, wp["title"], [], result)

    if open_only:
        result = [r for r in result if not r["done"]]

    if json_out:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if not result:
        print("  (no subtasks)")
        return

    for st in result:
        status = "✅" if st["done"] else "⬜"
        date = f"[{st['date']}]" if st["date"] else "[open]"
        print(f"  {st['id']}  {status}  {st['text']}  {date}")
        print(f"        └─ {st['project']} › {st['story']} › {st['task']}")


def _collect_subtasks_with_path(node, project, path, result):
    current_path = path + [node.title]
    if node.depth == 3:
        result.append({
            "id": node.id,
            "text": node.title,
            "date": node.date,
            "done": node.done,
            "project": project,
            "epic": current_path[0] if len(current_path) > 0 else "",
            "story": current_path[1] if len(current_path) > 1 else "",
            "task": current_path[2] if len(current_path) > 2 else "",
        })
    for child in node.children:
        _collect_subtasks_with_path(child, project, current_path, result)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_workflow_projects(client, root_id):
    """Get all child projects under the 'workflow' subproject."""
    subprojects = client.list_child_projects(root_id)
    workflow = next((p for p in subprojects if p["title"] == "workflow"), None)
    if not workflow:
        return []
    return client.list_child_projects(workflow["id"])


def get_workflow_parent_id(client, root_id):
    """Get the workflow subproject ID."""
    subprojects = client.list_child_projects(root_id)
    workflow = next((p for p in subprojects if p["title"] == "workflow"), None)
    if not workflow:
        print("ERROR: 'workflow' subproject not found. Run 'wardkeeper.py init' first.")
        sys.exit(1)
    return workflow["id"]


def find_task_project(client, task_id):
    """Get the project_id for a given task."""
    task = client.get_task(task_id)
    return task["project_id"]


# ─── Status check ────────────────────────────────────────────────────────────

def check_status(client, root_id):
    workflow_projects = get_workflow_projects(client, root_id)
    if not workflow_projects:
        print("PROJECT_MISSING: No projects found in workflow.")
        print("  Add one with:")
        print("    wardkeeper.py add project --name <project-name>")
        return True

    for wp in workflow_projects:
        tasks = client.get_project_tasks(wp["id"])
        tree = build_tree(tasks)

        if not tree:
            print(f"EPIC_MISSING {wp['id']}: Project '{wp['title']}' has no epics yet.")
            print(f"  Add with:")
            print(f"    wardkeeper.py add epic --project {wp['id']} --name <epic> [--vibe <vibe>]")
            return True

        for epic in tree:
            if not epic.children:
                print(f"STORY_MISSING {epic.id}: Epic '{epic.title[:50]}' has no stories yet.")
                print(f"  Add with:")
                print(f"    wardkeeper.py add story --epic {epic.id} --name <story>")
                return True

            for story in epic.children:
                if not story.children and "no_tasks" not in story.flags:
                    print(f"TASK_MISSING {story.id}: Story '{story.title[:50]}' has no tasks yet.")
                    print(f"  Add with:")
                    print(f"    wardkeeper.py add task --story {story.id} --name <task>")
                    print(f"  Or if no tasks needed:")
                    print(f"    wardkeeper.py done story {story.id}")
                    return True

                for task in story.children:
                    if not task.children and "no_subtasks" not in task.flags:
                        print(f"SUBTASK_MISSING {task.id}: Task '{task.title[:50]}' has no subtasks yet.")
                        print(f"  Add with:")
                        print(f"    wardkeeper.py add subtask --task {task.id} --text <text>")
                        print(f"  Or if no subtasks needed:")
                        print(f"    wardkeeper.py done task {task.id}")
                        return True

    print("OK: Everything complete.")
    print()
    navigate(client, root_id)
    return False


# ─── Navigate ────────────────────────────────────────────────────────────────

def navigate(client, root_id, node_id=None):
    if node_id is None:
        # Root level: show workflow projects
        print("NAVIGATE | root")
        print()
        workflow_projects = get_workflow_projects(client, root_id)
        if not workflow_projects:
            print("  (no projects)")
        for wp in workflow_projects:
            tasks = client.get_project_tasks(wp["id"])
            tree = build_tree(tasks)
            open_st = sum(1 for root in tree for s in collect_subtasks(root) if not s.done)
            print(f"  {wp['id']}  {wp['title']}  [{open_st} open subtasks]")
        print()
        print("Actions:")
        for wp in workflow_projects:
            print(f"  [{wp['id']}] open project  →  wardkeeper.py navigate {wp['id']}")
        print(f"  [n] new project        →  wardkeeper.py add project --name <name>")
        return

    # Check if node_id is a project or a task
    project = client.try_get_project(node_id)
    if project:
        # It's a project — show its epics
        tasks = client.get_project_tasks(node_id)
        tree = build_tree(tasks)
        print(f"NAVIGATE | {node_id} — {project['title']}")
        print()
        for epic in tree:
            sc = len(epic.children)
            print(f"  {epic.id}  🎯  {epic.title[:60]}  [{sc} stories]")
        print()
        print("Actions:")
        for epic in tree:
            print(f"  [{epic.id}] open epic  →  wardkeeper.py navigate {epic.id}")
        print(f"  [n] new epic       →  wardkeeper.py add epic --project {node_id} --name <name>")
        print(f"  [↑] back           →  wardkeeper.py navigate")
        return

    # It's a task — determine its level and show accordingly
    task_data = client.get_task(node_id)
    project_id = task_data["project_id"]
    all_tasks = client.get_project_tasks(project_id)
    tree = build_tree(all_tasks)
    node = find_node(tree, node_id)

    if not node:
        print(f"ERROR: ID {node_id} not found.")
        return

    print(f"NAVIGATE | {node_id} — {node.title}")
    print()

    if node.depth == 0:  # Epic → show stories
        for story in node.children:
            open_st = sum(1 for s in collect_subtasks(story) if not s.done)
            print(f"  {story.id}  🏁  {story.title}  [{open_st} open]")
        print()
        print("Actions:")
        for story in node.children:
            print(f"  [{story.id}] open story  →  wardkeeper.py navigate {story.id}")
        print(f"  [n] new story      →  wardkeeper.py add story --epic {node_id} --name <name>")
        for story in node.children:
            print(f"  [{story.id}x] delete  →  wardkeeper.py delete {story.id}")
        print(f"  [↑] back           →  wardkeeper.py navigate {project_id}")

    elif node.depth == 1:  # Story → show tasks
        for task in node.children:
            open_st = sum(1 for s in collect_subtasks(task) if not s.done)
            print(f"  {task.id}  ⚡  {task.title}  [{open_st} open subtasks]")
        print()
        print("Actions:")
        for task in node.children:
            print(f"  [{task.id}] open task  →  wardkeeper.py navigate {task.id}")
        print(f"  [n] new task       →  wardkeeper.py add task --story {node_id} --name <name>")
        for task in node.children:
            print(f"  [{task.id}x] delete  →  wardkeeper.py delete {task.id}")
        print(f"  [↑] back           →  wardkeeper.py navigate {node.parent_id}")

    elif node.depth == 2:  # Task → show subtasks
        for st in node.children:
            status = "✅" if st.done else "⬜"
            date = f"[{st.date}]" if st.date else "[open]"
            print(f"  {st.id}  {status}  {st.title}  {date}")
        print()
        print("Actions:")
        print(f"  [n]  add subtask  →  wardkeeper.py add subtask --task {node_id} --text <text>")
        for st in node.children:
            if not st.done:
                print(f"  [{st.id}d] mark done  →  wardkeeper.py set subtask {st.id} --done")
                print(f"  [{st.id}t] set date   →  wardkeeper.py set subtask {st.id} --date <YYYY-MM-DD>")
            print(f"  [{st.id}x] delete    →  wardkeeper.py delete {st.id}")
        print(f"  [↑]  back         →  wardkeeper.py navigate {node.parent_id}")


# ─── Add commands ────────────────────────────────────────────────────────────

def add_project(client, root_id, name):
    wf_id = get_workflow_parent_id(client, root_id)
    p = client.create_project(name.upper(), parent_id=wf_id)
    print(f"OK: Project '{p['title']}' created (id={p['id']})")
    check_status(client, root_id)


def add_epic(client, root_id, project_id, names, vibe=""):
    for name in names:
        desc = build_description(body=vibe)  # no parent marker — epics are root
        task = client.create_task(project_id, name, description=desc)
        print(f"OK: Epic '{name[:50]}' created (id={task['id']})")
    check_status(client, root_id)


def add_story(client, root_id, epic_id, names):
    project_id = find_task_project(client, epic_id)
    for name in names:
        desc = build_description(parent_id=epic_id)
        task = client.create_task(project_id, name, description=desc)
        client.create_relation(epic_id, task["id"])
        print(f"OK: Story '{name[:50]}' created (id={task['id']})")
    check_status(client, root_id)


def add_task(client, root_id, story_id, names):
    project_id = find_task_project(client, story_id)
    for name in names:
        desc = build_description(parent_id=story_id)
        task = client.create_task(project_id, name, description=desc)
        client.create_relation(story_id, task["id"])
        print(f"OK: Task '{name[:50]}' created (id={task['id']})")
    check_status(client, root_id)


def add_subtask(client, root_id, task_id, texts):
    project_id = find_task_project(client, task_id)
    for text in texts:
        desc = build_description(parent_id=task_id)
        task = client.create_task(project_id, text, description=desc)
        client.create_relation(task_id, task["id"])
        print(f"OK: Subtask '{text[:50]}' created (id={task['id']})")
    check_status(client, root_id)


# ─── Done / set / delete ────────────────────────────────────────────────────

def set_subtask(client, task_id, date=None, done=False, text=None):
    updates = {}
    if date:
        updates["due_date"] = f"{date}T00:00:00Z"
        # Also update description marker
        task = client.get_task(task_id)
        parsed = parse_description(task.get("description", ""))
        new_desc = build_description(
            body=parsed["body"], parent_id=parsed["parent_id"],
            flags=parsed["flags"], date=date
        )
        updates["description"] = new_desc
        print(f"OK: Date set → {date}")
    if done:
        updates["done"] = True
        print(f"OK: Marked as done.")
    if text:
        updates["title"] = text
        print(f"OK: Text updated.")
    if updates:
        client.update_task(task_id, **updates)


def mark_done(client, root_id, node_type, task_id):
    task = client.get_task(task_id)
    parsed = parse_description(task.get("description", ""))
    flag = "no_tasks" if node_type == "story" else "no_subtasks"
    parsed["flags"].add(flag)
    new_desc = build_description(
        body=parsed["body"], parent_id=parsed["parent_id"],
        flags=parsed["flags"], date=parsed["date"]
    )
    client.update_task(task_id, description=new_desc)
    label = "Story" if node_type == "story" else "Task"
    print(f"OK: {label} {task_id} — no {node_type.replace('story', 'tasks').replace('task', 'subtasks')} needed.")
    check_status(client, root_id)


def delete_node(client, root_id, node_id):
    # Try as project first
    workflow_projects = get_workflow_projects(client, root_id)
    for wp in workflow_projects:
        if wp["id"] == node_id:
            client.delete_project(node_id)
            print(f"OK: Project '{wp['title']}' deleted.")
            navigate(client, root_id)
            return

    # It's a task — cascade delete
    project_id = find_task_project(client, node_id)
    all_tasks = client.get_project_tasks(project_id)
    tree = build_tree(all_tasks)
    node = find_node(tree, node_id)

    if not node:
        print(f"ERROR: ID {node_id} not found.")
        return

    # Collect all descendants and delete bottom-up
    all_ids = collect_all_descendants(node)
    all_ids.reverse()  # leaves first
    for tid in all_ids:
        client.delete_task(tid)

    print(f"OK: {node.type_name.title()} '{node.title[:50]}' deleted ({len(all_ids)} items).")

    # Navigate to parent
    if node.parent_id:
        navigate(client, root_id, node.parent_id)
    else:
        navigate(client, root_id, project_id)


# ─── Init ────────────────────────────────────────────────────────────────────

def cmd_init(client):
    # Check if root already exists
    cfg = load_config()
    existing_root = int(cfg.get("root_id", "0"))
    if existing_root:
        try:
            p = client.get_project(existing_root)
            print(f"Root project already exists: '{p['title']}' (id={existing_root})")
            # Check subprojects
            children = client.list_child_projects(existing_root)
            existing_titles = {c["title"] for c in children}
            for sub in SUBPROJECTS:
                if sub not in existing_titles:
                    sp = client.create_project(sub, parent_id=existing_root)
                    print(f"  Created missing subproject: {sub} (id={sp['id']})")
                else:
                    print(f"  ✓ {sub}")
            return
        except SystemExit:
            pass

    # Create root project
    root = client.create_project("WARDKEEPER")
    root_id = root["id"]
    print(f"Created root project: WARDKEEPER (id={root_id})")

    # Create subprojects
    for sub in SUBPROJECTS:
        sp = client.create_project(sub, parent_id=root_id)
        print(f"  Created: {sub} (id={sp['id']})")

    # Save root_id to config
    save_root_id(root_id)
    print(f"\nroot_id={root_id} saved to wardkeeper.cfg")
    print("Init complete.")


# ─── Migrate ─────────────────────────────────────────────────────────────────

def cmd_migrate(client, root_id, dry_run=False):
    # Find old projects.json
    old_file = BASE_DIR.parent / "MD-FILES" / "data" / "projects.json"
    if not old_file.exists():
        old_file = BASE_DIR / "data" / "projects.json"
    if not old_file.exists():
        print(f"ERROR: projects.json not found at {old_file}")
        sys.exit(1)

    data = json.loads(old_file.read_text(encoding="utf-8"))
    if not data.get("projects"):
        print("No projects to migrate.")
        return

    wf_id = get_workflow_parent_id(client, root_id)

    for p in data["projects"]:
        name = p["name"]
        if dry_run:
            print(f"[DRY] Would create project: {name}")
        else:
            proj = client.create_project(name, parent_id=wf_id)
            print(f"Created project: {name} (id={proj['id']})")
            proj_id = proj["id"]

        for g in p.get("goals", []):
            vibe = g.get("vibe", "")
            if dry_run:
                print(f"  [DRY] Epic: {g['name'][:60]}")
            else:
                desc = build_description(body=vibe)  # no parent marker for epics
                epic = client.create_task(proj_id, g["name"], description=desc)
                print(f"  Epic: {g['name'][:60]} (id={epic['id']})")

            for m in g.get("milestones", []):
                flags = set()
                if m.get("no_tasks"):
                    flags.add("no_tasks")
                if dry_run:
                    print(f"    [DRY] Story: {m['name'][:50]}")
                else:
                    desc = build_description(parent_id=epic["id"], flags=flags)
                    story = client.create_task(proj_id, m["name"], description=desc)
                    client.create_relation(epic["id"], story["id"])
                    print(f"    Story: {m['name'][:50]} (id={story['id']})")

                for t in m.get("tasks", []):
                    t_flags = set()
                    if t.get("no_subtasks"):
                        t_flags.add("no_subtasks")
                    if dry_run:
                        print(f"      [DRY] Task: {t['name'][:50]}")
                    else:
                        desc = build_description(parent_id=story["id"], flags=t_flags)
                        task = client.create_task(proj_id, t["name"], description=desc)
                        client.create_relation(story["id"], task["id"])
                        print(f"      Task: {t['name'][:50]} (id={task['id']})")

                    for ns in t.get("next_steps", []):
                        ns_date = ns.get("date")
                        if dry_run:
                            print(f"        [DRY] Subtask: {ns['text'][:50]}")
                        else:
                            desc = build_description(
                                parent_id=task["id"],
                                date=ns_date
                            )
                            st = client.create_task(proj_id, ns["text"], description=desc)
                            client.create_relation(task["id"], st["id"])
                            updates = {}
                            if ns.get("done"):
                                updates["done"] = True
                            if ns_date:
                                updates["due_date"] = f"{ns_date}T00:00:00Z"
                            if updates:
                                client.update_task(st["id"], **updates)
                            status = "✅" if ns.get("done") else "⬜"
                            print(f"        Subtask: {status} {ns['text'][:50]} (id={st['id']})")

    print("\nMigration complete." if not dry_run else "\nDry run complete.")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="WARDKEEPER — Vikunja project tree manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="command")

    # init
    sub.add_parser("init")

    # migrate
    p_mig = sub.add_parser("migrate")
    p_mig.add_argument("--dry-run", action="store_true")

    # list
    p_list = sub.add_parser("list")
    p_list.add_argument("--json", action="store_true")

    # subtasks
    p_ns = sub.add_parser("subtasks")
    p_ns.add_argument("--open", action="store_true")
    p_ns.add_argument("--json", action="store_true")

    # navigate
    p_nav = sub.add_parser("navigate")
    p_nav.add_argument("node_id", nargs="?", default=None, type=int)

    # add
    p_add = sub.add_parser("add")
    p_add.add_argument("node_type", choices=["project", "epic", "story", "task", "subtask"])
    p_add.add_argument("--name", nargs="+")
    p_add.add_argument("--text", nargs="+")
    p_add.add_argument("--vibe")
    p_add.add_argument("--project", type=int)
    p_add.add_argument("--epic", type=int)
    p_add.add_argument("--story", type=int)
    p_add.add_argument("--task", type=int)

    # set
    p_set = sub.add_parser("set")
    p_set.add_argument("node_type", choices=["subtask"])
    p_set.add_argument("node_id", type=int)
    p_set.add_argument("--date")
    p_set.add_argument("--done", action="store_true")
    p_set.add_argument("--text")

    # delete
    p_del = sub.add_parser("delete")
    p_del.add_argument("node_id", type=int)

    # done
    p_done = sub.add_parser("done")
    p_done.add_argument("node_type", choices=["story", "task"])
    p_done.add_argument("node_id", type=int)

    args = parser.parse_args()
    cfg = load_config()
    client = VikunjaClient(cfg["url"], cfg["token"])
    root_id = int(cfg.get("root_id", "0"))

    if args.command == "init":
        cmd_init(client)

    elif args.command == "migrate":
        if not root_id:
            print("ERROR: root_id not set. Run 'wardkeeper.py init' first.")
            sys.exit(1)
        cmd_migrate(client, root_id, dry_run=args.dry_run)

    elif args.command == "list":
        display_tree(client, root_id, json_out=args.json)

    elif args.command == "subtasks":
        display_subtasks(client, root_id, open_only=args.open, json_out=args.json)

    elif args.command == "navigate":
        navigate(client, root_id, args.node_id)

    elif args.command == "add":
        t = args.node_type
        if t == "project":
            if not args.name:
                print("ERROR: --name required"); sys.exit(1)
            add_project(client, root_id, args.name[0])
        elif t == "epic":
            if not args.project or not args.name:
                print("ERROR: --project and --name required"); sys.exit(1)
            add_epic(client, root_id, args.project, args.name, vibe=args.vibe or "")
        elif t == "story":
            if not args.epic or not args.name:
                print("ERROR: --epic and --name required"); sys.exit(1)
            add_story(client, root_id, args.epic, args.name)
        elif t == "task":
            if not args.story or not args.name:
                print("ERROR: --story and --name required"); sys.exit(1)
            add_task(client, root_id, args.story, args.name)
        elif t == "subtask":
            if not args.task or not args.text:
                print("ERROR: --task and --text required"); sys.exit(1)
            add_subtask(client, root_id, args.task, args.text)

    elif args.command == "set":
        set_subtask(client, args.node_id,
                    date=args.date, done=args.done, text=args.text)

    elif args.command == "delete":
        delete_node(client, root_id, args.node_id)

    elif args.command == "done":
        mark_done(client, root_id, args.node_type, args.node_id)

    else:
        if not root_id:
            print("ERROR: Not initialized. Run 'wardkeeper.py init' first.")
            return
        check_status(client, root_id)


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
