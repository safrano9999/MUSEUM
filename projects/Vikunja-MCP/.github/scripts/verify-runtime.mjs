// Runs only inside the disposable CI container, against its empty SQLite DB.
import assert from 'node:assert/strict';
import { randomBytes } from 'node:crypto';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
const require = createRequire('/opt/supergateway/package.json');
assert.equal(JSON.parse(readFileSync('/opt/supergateway/package.json')).version, '4.1.0');
assert.equal(JSON.parse(readFileSync('/opt/supergateway/node_modules/@modelcontextprotocol/sdk/package.json')).version, '1.30.0');
const { Client } = await import(require.resolve('@modelcontextprotocol/sdk/client/index.js'));
const { StreamableHTTPClientTransport } = await import(require.resolve('@modelcontextprotocol/sdk/client/streamableHttp.js'));
const api = 'http://127.0.0.1:3456/api/v1';
const endpoint = 'http://127.0.0.1:8000/mcp';
const password = randomBytes(24).toString('hex');
let bearer = '';
async function request(path, method = 'GET', body, authenticated = true) {
  const response = await fetch(api + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(authenticated && bearer ? { Authorization: `Bearer ${bearer}` } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  assert(response.ok, `${method} ${path}: HTTP ${response.status}`);
  return response.json();
}
const info = await request('/info');
assert.match(info.version, /^v?2\.6\.0(?:$|[-+])/);
for (const username of ['ci_owner', 'ci_member']) {
  await request('/register', 'POST', { username, password, email: `${username}@example.invalid` }, false);
}
bearer = (await request('/login', 'POST', { username: 'ci_owner', password }, false)).token;
assert(bearer);
const client = new Client({ name: 'vikunja-image-verification', version: '1' });
const transport = new StreamableHTTPClientTransport(new URL(endpoint), { requestInit: { headers: { Authorization: `Bearer ${bearer}` } } });
await client.connect(transport);
async function tool(name, args) {
  const result = await client.callTool({ name, arguments: args });
  assert(!result.isError, `${name} failed: ${JSON.stringify(result.content)}`);
  return result;
}
try {
  const tools = (await client.listTools()).tools;
  for (const name of ['vikunja_teams', 'vikunja_task_crud', 'vikunja_task_bulk']) {
    assert(tools.some(t => t.name === name), `Missing ${name}`);
  }
  await tool('vikunja_teams', { subcommand: 'create', name: 'ci-team', description: 'preserve description', isPublic: true });
  const team = (await request('/teams')).find(t => t.name === 'ci-team');
  assert(team?.id);
  assert.equal(team.is_public, true);
  await tool('vikunja_teams', { subcommand: 'get', id: team.id });
  await tool('vikunja_teams', { subcommand: 'update', id: team.id, name: 'ci-team-renamed' });
  const changedTeam = await request(`/teams/${team.id}`);
  assert.equal(changedTeam.description, 'preserve description');
  assert.equal(changedTeam.is_public, true);
  await tool('vikunja_teams', { subcommand: 'members', memberSubcommand: 'add', id: team.id, username: 'ci_member' });
  await tool('vikunja_teams', { subcommand: 'members', memberSubcommand: 'list', id: team.id });
  for (const admin of [true, true, false]) {
    await tool('vikunja_teams', { subcommand: 'members', memberSubcommand: 'update', id: team.id, username: 'ci_member', admin });
    const member = (await request(`/teams/${team.id}`)).members.find(m => m.username === 'ci_member');
    assert.equal(member.admin, admin, 'Admin update must be idempotent');
  }
  await tool('vikunja_teams', { subcommand: 'members', memberSubcommand: 'remove', id: team.id, username: 'ci_member' });
  assert(!(await request(`/teams/${team.id}`)).members.some(m => m.username === 'ci_member'));
  const project = await request('/projects', 'PUT', { title: 'ci-bulk-project' });
  const dueDate = '2030-01-15T12:00:00Z';
  const tasks = Array.from({ length: 6 }, (_, i) => ({ title: `ci-task-${i}`, dueDate, repeatAfter: 2, repeatMode: 'day' }));
  await tool('vikunja_task_bulk', { operation: 'bulk-create', projectId: project.id, tasks });
  const stored = await request(`/projects/${project.id}/tasks`);
  assert.equal(stored.length, tasks.length, 'All bulk tasks must persist');
  for (const task of stored) {
    assert.equal(Date.parse(task.due_date), Date.parse(dueDate));
    assert.equal(task.repeat_after, 2 * 24 * 60 * 60);
    assert.equal(task.repeat_mode, 0);
  }
  await tool('vikunja_task_crud', { operation: 'list' });
  const wrongSessionBearer = await fetch(endpoint, {
    method: 'POST',
    headers: { Authorization: 'Bearer incorrect-ci-token', 'Mcp-Session-Id': transport.sessionId,
      'Content-Type': 'application/json', Accept: 'application/json, text/event-stream' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/list' }),
  });
  assert.equal(wrongSessionBearer.status, 401);
  await tool('vikunja_teams', { subcommand: 'delete', id: team.id });
  assert(!(await request('/teams')).some(t => t.id === team.id));
  console.log(JSON.stringify({ status: 'PASS', vikunja: info.version, tools: tools.length,
    checks: ['team fields', 'members by username', 'idempotent admin changes', 'bulk dates/repeats', 'all-tasks route', 'session bearer isolation'] }));
} finally {
  await client.close();
}
