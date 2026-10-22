#!/usr/bin/env python3
# Source of truth: SCRIPTS/githubactions. Generated copies are overwritten.

import hashlib
import sys
from pathlib import Path

TASK_SHA256 = "a77217ee683187458d91246e2d3986543d04323e39b8595468ff8a2324daf515"
TEAMS_SHA256 = "b8a3d8c0407ee04076359bdd2618dfb3f5ca2952b345c51bda529821c1c8a8ea"
BULK_OPERATIONS_SHA256 = "62d27244fa4a4da23b291ef0414e0fc4f2aa275194b87e21bd5e37e67b8ec585"
TASK_BULK_SHA256 = "7082b29aaebbc56ab4dc2365c0424d2f54f283897133eab38c4c57a8abd8b012"


def checked_source(path: Path, expected: str) -> str:
    source = path.read_text()
    actual = hashlib.sha256(source.encode()).hexdigest()
    if actual != expected:
        raise SystemExit(f"unexpected source hash: {path}: {actual}")
    return source


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, got {count}")
    return source.replace(old, new, 1)


def replace_count(source: str, old: str, new: str, count: int, label: str) -> str:
    actual = source.count(old)
    if actual != count:
        raise SystemExit(f"{label}: expected {count} anchors, got {actual}")
    return source.replace(old, new)


def replace_block(source: str, start: str, end: str, replacement: str, label: str) -> str:
    if source.count(start) != 1 or source.count(end) != 1:
        raise SystemExit(f"{label}: block anchors are not unique")
    left, tail = source.split(start, 1)
    _, right = tail.split(end, 1)
    return left + replacement + end + right


if len(sys.argv) != 2:
    raise SystemExit("usage: patch-vikunja-mcp.py REPOSITORY_ROOT")

root = Path(sys.argv[1])
task_path = root / "node_modules/node-vikunja/dist/esm/services/task.service.js"
teams_path = root / "src/tools/teams.ts"
bulk_operations_path = root / "src/tools/tasks/bulk-operations-simplified.ts"
task_bulk_path = root / "src/tools/task-bulk.ts"
task = checked_source(task_path, TASK_SHA256)
teams = checked_source(teams_path, TEAMS_SHA256)
bulk_operations = checked_source(bulk_operations_path, BULK_OPERATIONS_SHA256)
task_bulk = checked_source(task_bulk_path, TASK_BULK_SHA256)

task = replace_once(
    task,
    "this.request('/tasks/all', 'GET'",
    "this.request('/tasks', 'GET'",
    "node-vikunja all-tasks route",
)

teams = replace_once(
    teams,
    "import type { Team } from 'node-vikunja';",
    "import type { Team, JSONObject } from 'node-vikunja';",
    "node-vikunja JSON types",
)
teams = replace_once(
    teams,
    """interface TeamListParams {
  page?: number;
  per_page?: number;
  s?: string;
}
""",
    """interface TeamListParams {
  page?: number;
  per_page?: number;
  s?: string;
}

interface TeamMemberView extends JSONObject {
  id: number;
  username: string;
  admin: boolean;
  created?: string;
}

interface TeamWithMembers extends Team {
  members?: TeamMemberView[];
  is_public?: boolean;
}
""",
    "team response types",
)
teams = replace_once(teams, "page: z.number().positive().optional()", "page: z.number().int().positive().optional()", "page schema")
teams = replace_once(teams, "perPage: z.number().positive().max(100).optional()", "perPage: z.number().int().positive().max(100).optional()", "per-page schema")
teams = replace_once(
    teams,
    """      name: z.string().optional(),
      description: z.string().optional(),
""",
    """      name: z.string().min(1).max(250).optional(),
      description: z.string().optional(),
      isPublic: z.boolean().optional(),
""",
    "team schema",
)
teams = replace_once(
    teams,
    """      try {

        switch (subcommand) {
""",
    """      try {
        const session = authManager.getSession();
        const apiUrl = session.apiUrl.replace(/\\/+$/, '');
        const fetchTeam = async (teamId: number, operation: string): Promise<TeamWithMembers> => {
          const response = await fetch(`${session.apiUrl}/teams/${teamId}`, {
            method: 'GET',
            headers: {
              Authorization: `Bearer ${session.apiToken}`,
              'Content-Type': 'application/json',
            },
          });
          if (!response.ok) {
            const errorText = await response.text();
            throw handleStatusCodeError(
              { statusCode: response.status, message: errorText },
              operation,
              teamId,
              `Failed to ${operation} ${teamId}: ${errorText}`,
            );
          }
          return (await response.json()) as TeamWithMembers;
        };

        switch (subcommand) {
""",
    "shared team fetch",
)
teams = replace_once(
    teams,
    """            const teamData: Partial<Team> = {
              name: args.name,
            };
            if (args.description !== undefined) {
              teamData.description = args.description;
            }
""",
    """            const teamData: Partial<Team> & { is_public?: boolean } = {
              name: args.name,
            };
            if (args.description !== undefined) teamData.description = args.description;
            if (args.isPublic !== undefined) teamData.is_public = args.isPublic;
""",
    "team create fields",
)

teams = replace_block(
    teams,
    "          case 'get': {\n",
    "\n          case 'update': {",
    """          case 'get': {
            if (args.id === undefined) {
              throw new MCPError(ErrorCode.VALIDATION_ERROR, 'Team ID is required');
            }

            const teamId = validateAndConvertId(args.id, 'id');
            const team = await fetchTeam(teamId, 'get team');
            const standardResponse = createStandardResponse(
              'get-team',
              `Retrieved team "${team.name}"`,
              { team },
              { teamId },
            );

            return {
              content: [{ type: 'text', text: formatAorpAsMarkdown(standardResponse) }],
            };
          }
""",
    "get team",
)
teams = replace_block(
    teams,
    """          case 'update': {
            if (args.id === undefined) {
""",
    "\n          case 'delete': {",
    """          case 'update': {
            if (args.id === undefined) {
              throw new MCPError(ErrorCode.VALIDATION_ERROR, 'Team ID is required');
            }
            if (args.name === undefined && args.description === undefined && args.isPublic === undefined) {
              throw new MCPError(ErrorCode.VALIDATION_ERROR, 'At least one field to update is required');
            }

            const teamId = validateAndConvertId(args.id, 'id');
            const currentTeam = await fetchTeam(teamId, 'get team for update');
            const updateData = {
              name: args.name ?? currentTeam.name,
              description: args.description ?? currentTeam.description ?? '',
              is_public: args.isPublic ?? currentTeam.is_public ?? false,
            };
            const affectedFields: string[] = [];
            if (args.name !== undefined) affectedFields.push('name');
            if (args.description !== undefined) affectedFields.push('description');
            if (args.isPublic !== undefined) affectedFields.push('isPublic');

            const response = await fetch(`${session.apiUrl}/teams/${teamId}`, {
              method: 'POST',
              headers: {
                Authorization: `Bearer ${session.apiToken}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(updateData),
            });
            if (!response.ok) {
              const errorText = await response.text();
              throw handleStatusCodeError(
                { statusCode: response.status, message: errorText },
                'update team',
                teamId,
                `Failed to update team ${teamId}: ${errorText}`,
              );
            }

            const team = (await response.json()) as TeamWithMembers;
            const standardResponse = createStandardResponse(
              'update-team',
              `Team "${team.name}" updated successfully`,
              { team },
              { teamId, affectedFields },
            );
            return {
              content: [{ type: 'text', text: formatAorpAsMarkdown(standardResponse) }],
            };
          }
""",
    "update team",
)
teams = replace_once(teams, "              const session = authManager.getSession();\n", "", "delete session")
teams = replace_once(teams, "'leave team'", "'delete team'", "delete operation name")
teams = replace_once(teams, "Failed to leave team", "Failed to delete team", "delete error message")
teams = replace_once(teams, "            const session = authManager.getSession();\n", "", "members session")

teams = replace_block(
    teams,
    "              case 'list': {\n",
    "\n              case 'add': {",
    """              case 'list': {
                const team = await fetchTeam(teamId, 'list members for team');
                const members = team.members ?? [];
                const standardResponse = createStandardResponse(
                  'list-team-members',
                  `Retrieved ${members.length} member${members.length !== 1 ? 's' : ''}`,
                  { members },
                  { teamId, count: members.length },
                );
                return {
                  content: [{ type: 'text', text: formatAorpAsMarkdown(standardResponse) }],
                };
              }
""",
    "list team members",
)
teams = replace_block(
    teams,
    """              case 'update': {
                if (args.userId === undefined) {
""",
    "\n              default:",
    """              case 'update': {
                if (args.username === undefined) {
                  throw new MCPError(ErrorCode.VALIDATION_ERROR, 'Username is required');
                }
                if (args.admin === undefined) {
                  throw new MCPError(ErrorCode.VALIDATION_ERROR, 'Admin flag is required for updating member');
                }

                const username = args.username;
                const team = await fetchTeam(teamId, 'get team member from team');
                const currentMember = team.members?.find(member => member.username === username);
                if (!currentMember) {
                  throw new MCPError(ErrorCode.NOT_FOUND, `User "${username}" is not a member of team ${teamId}`);
                }

                const changed = currentMember.admin !== args.admin;
                let member = currentMember;
                if (changed) {
                  const response = await fetch(
                    `${session.apiUrl}/teams/${teamId}/members/${encodeURIComponent(username)}/admin`,
                    {
                      method: 'POST',
                      headers: {
                        Authorization: `Bearer ${session.apiToken}`,
                        'Content-Type': 'application/json',
                      },
                    },
                  );
                  if (!response.ok) {
                    const errorText = await response.text();
                    throw handleStatusCodeError(
                      { statusCode: response.status, message: errorText },
                      'update team member',
                      teamId,
                      `Failed to update user ${username} in team ${teamId}: ${errorText}`,
                    );
                  }
                  const updatedTeam = await fetchTeam(teamId, 'verify team member in team');
                  const updatedMember = updatedTeam.members?.find(item => item.username === username);
                  if (!updatedMember) {
                    throw new MCPError(ErrorCode.NOT_FOUND, `User "${username}" is not a member of team ${teamId}`);
                  }
                  member = updatedMember;
                }

                const standardResponse = createStandardResponse(
                  'update-team-member',
                  `Admin status for user "${username}" is now ${args.admin ? 'enabled' : 'disabled'}`,
                  { member },
                  { teamId, username, admin: args.admin, changed },
                );
                return {
                  content: [{ type: 'text', text: formatAorpAsMarkdown(standardResponse) }],
                };
              }
""",
    "update team member",
)

teams = replace_count(teams, "userId", "username", 17, "member username contract")
teams = replace_once(
    teams,
    "username: z.union([z.string(), z.number()]).optional()",
    "username: z.string().min(1).max(250).optional()",
    "member username schema",
)
teams = replace_count(teams, "User ID is required", "Username is required", 2, "member validation messages")
teams = replace_count(
    teams,
    "const username = validateAndConvertId(args.username, 'username');",
    "const username = args.username;",
    2,
    "member username parsing",
)
teams = replace_once(teams, "username: String(username)", "username", "member add payload")
teams = replace_once(
    teams,
    "`${session.apiUrl}/teams/${teamId}/members/${username}`",
    "`${session.apiUrl}/teams/${teamId}/members/${encodeURIComponent(username)}`",
    "member removal URL",
)
teams = replace_once(
    teams,
    "const result = await response.json();",
    "const result = (await response.json()) as { message: string };",
    "member removal response",
)
teams = replace_once(teams, "{ message: result },", "{ message: result.message },", "member removal message")
teams = replace_count(teams, "${session.apiUrl}/teams", "${apiUrl}/teams", 6, "normalized API URLs")

bulk_operations = replace_once(
    bulk_operations,
    "create: new BatchProcessor({ maxConcurrency: 8, batchSize: 15, enableMetrics: true, batchDelay: 0 })",
    "create: new BatchProcessor({ maxConcurrency: 1, batchSize: 15, enableMetrics: true, batchDelay: 0 })",
    "serialize task creation",
)
task_bulk = replace_once(
    task_bulk,
    "const filteredTask: { title: string; description?: string; due_date?: string; priority?: number; labels?: number[]; assignees?: number[]; repeat_after?: number; repeat_mode?: 'day' | 'week' | 'month' | 'year' }",
    "const filteredTask: { title: string; description?: string; dueDate?: string; priority?: number; labels?: number[]; assignees?: number[]; repeatAfter?: number; repeatMode?: 'day' | 'week' | 'month' | 'year' }",
    "bulk task field types",
)
task_bulk = replace_once(task_bulk, "filteredTask.due_date = task.dueDate", "filteredTask.dueDate = task.dueDate", "bulk due date")
task_bulk = replace_once(task_bulk, "filteredTask.repeat_after = task.repeatAfter", "filteredTask.repeatAfter = task.repeatAfter", "bulk repeat interval")
task_bulk = replace_once(task_bulk, "filteredTask.repeat_mode = task.repeatMode", "filteredTask.repeatMode = task.repeatMode", "bulk repeat mode")

required = (
    "username: z.string().min(1).max(250).optional()",
    "is_public: args.isPublic ?? currentTeam.is_public ?? false",
    "const members = team.members ?? [];",
    "members/${encodeURIComponent(username)}/admin",
    "const changed = currentMember.admin !== args.admin;",
)
for needle in required:
    if teams.count(needle) != 1:
        raise SystemExit(f"team patch postcondition failed: {needle!r}")
for stale in ("userId", "method: 'PUT',\n              headers"):
    if stale in teams:
        raise SystemExit(f"stale team implementation remains: {stale!r}")
if task.count("this.request('/tasks', 'GET'") != 1:
    raise SystemExit("task route patch postcondition failed")
if bulk_operations.count("create: new BatchProcessor({ maxConcurrency: 1") != 1:
    raise SystemExit("bulk create serialization postcondition failed")
for needle in ("filteredTask.dueDate", "filteredTask.repeatAfter", "filteredTask.repeatMode"):
    if task_bulk.count(needle) != 1:
        raise SystemExit(f"bulk task field postcondition failed: {needle!r}")

# All transformations are validated before any source file is changed.
task_path.write_text(task)
teams_path.write_text(teams)
bulk_operations_path.write_text(bulk_operations)
task_bulk_path.write_text(task_bulk)
