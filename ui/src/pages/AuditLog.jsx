import { useEffect, useMemo, useState } from 'react'
import { Table, Tag, Card, Input, Typography } from 'antd'
import { api } from '../api'

const STATUS_COLOR = {
  OK: 'green', PENDING_APPROVAL: 'gold', REJECTED: 'red',
  BLOCKED: 'red', ERROR: 'red', INFO_REQUIRED: 'orange', ESCALATED: 'purple',
}
const TOOL_LABEL = {
  search_kb: '检索知识库', query_user_profile: '查询员工', query_system_status: '查询系统状态',
  check_permission_policy: '检查权限策略', grant_permission: '授予权限', create_incident_task: '创建任务',
}

export default function AuditLog() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [tid, setTid] = useState('')

  const load = async (ticketId = '') => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (ticketId) params.set('ticket_id', ticketId)
      setRows((await api.audit(`?${params.toString()}`)).items)
    } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])
  useEffect(() => { load(tid.trim()) }, [tid])

  const columns = useMemo(() => [
    {
      title: '时间', dataIndex: 'ts', width: 150,
      render: (v) => <span className="mono">{v}</span>,
    },
    { title: '工单', dataIndex: 'ticket_id', width: 90, render: (v) => <span className="mono">{v}</span> },
    {
      title: '工具', dataIndex: 'tool_name', width: 130,
      render: (v) => <Tag color="blue">{TOOL_LABEL[v] || v}</Tag>,
    },
    { title: '状态', dataIndex: 'status', width: 130, render: (v) => <Tag color={STATUS_COLOR[v]}>{v}</Tag> },
    {
      title: '风险', dataIndex: 'risk_level', width: 80,
      render: (v) => <Tag color={v === 'HIGH' ? 'red' : v === 'MEDIUM' ? 'orange' : 'green'}>{v || '—'}</Tag>,
    },
    { title: '调用者', dataIndex: 'caller_role', width: 100, render: (v) => (v ? String(v) : '—') },
    {
      title: '输入', dataIndex: 'input_json', width: 220,
      render: (v) => <span className="mono" style={{ color: '#7a8699' }}>{v ? JSON.stringify(v) : '—'}</span>,
    },
    {
      title: '决策 / 结果', dataIndex: 'reason',
      render: (v) => <Typography.Text style={{ fontSize: 12 }}>{v || '—'}</Typography.Text>,
    },
  ], [])

  return (
    <div className="page">
      <h1 className="page-title">审计日志</h1>
      <div className="page-sub">Tool Gateway 每次工具调用的不可变证据 · 支持按工单号过滤</div>

      <Card>
        <Input.Search
          placeholder="按工单号过滤（如 T-1022）"
          allowClear style={{ width: 280, marginBottom: 14 }}
          onSearch={(v) => load(v.trim())}
        />
        <Table
          rowKey="invocation_id"
          size="small"
          loading={loading}
          dataSource={rows}
          columns={columns}
          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  )
}