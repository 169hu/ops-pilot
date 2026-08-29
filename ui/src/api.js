const BASE = '/api'

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败(${res.status})`)
  }
  return res.json()
}

export const api = {
  tickets: (params = '') => req(`/tickets${params}`),
  ticket: (id) => req(`/tickets/${id}`),
  run: (id) => req(`/tickets/${id}/run`, { method: 'POST' }),
  approvals: () => req('/approvals'),
  approve: (id) => req(`/approvals/${id}/approve`, { method: 'POST' }),
  audit: (params = '') => req(`/audit${params}`),
  evalReport: () => req('/eval'),
  tools: () => req('/tools'),
}

export const RISK_COLOR = { HIGH: 'red', MEDIUM: 'orange', LOW: 'green' }
export const RISK_TEXT = { HIGH: '高', MEDIUM: '中', LOW: '低' }
export const INTENTS = {
  general_query: '普通咨询',
  system_fault: '系统故障',
  permission_request: '权限申请',
  high_risk_request: '高风险权限',
  attack: '攻击/越权',
}

export const infoFrom = (row) => ({
  tool: row.tool,
  status: row.status,
  reason: row.reason || '',
})