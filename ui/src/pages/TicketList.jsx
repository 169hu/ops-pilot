import { useEffect, useMemo, useState } from 'react'
import { Table, Tag, Button, Input, Segmented, Space } from 'antd'
import { ReloadOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api, RISK_COLOR, RISK_TEXT, INTENTS } from '../api'

const CATS = [
  { value: '', label: '全部' },
  { value: 'general_query', label: '咨询' },
  { value: 'system_fault', label: '故障' },
  { value: 'permission_request', label: '权限' },
  { value: 'high_risk_request', label: '高风险' },
  { value: 'attack', label: '攻击' },
]

export default function TicketList() {
  const nav = useNavigate()
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [cat, setCat] = useState('')
  const [q, setQ] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (cat) params.set('category', cat)
      if (q) params.set('q', q)
      const res = await api.tickets(`?${params.toString()}`)
      setData(res.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [cat])

  const run = async (record, e) => {
    e.stopPropagation()
    await api.run(record.ticket_id)
    load()
  }

  const columns = useMemo(() => [
    {
      title: '工单号', dataIndex: 'ticket_id', width: 90,
      render: (v) => <span className="mono">{v}</span>,
    },
    {
      title: '描述', dataIndex: 'description', ellipsis: true,
      render: (v, r) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => nav(`/tickets/${r.ticket_id}`)}>
          {v}
        </Button>
      ),
    },
    {
      title: '类别', dataIndex: 'category', width: 110,
      render: (v) => <Tag>{INTENTS[v] || v}</Tag>,
    },
    {
      title: '风险', dataIndex: 'risk_level', width: 80,
      render: (v) => <Tag color={RISK_COLOR[v]}>{RISK_TEXT[v]}</Tag>,
    },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (v, r) => {
        const next = r?.last_run?.next_action
        const label = next || v
        const color = label === 'WAITING_APPROVAL' ? 'gold'
          : label === 'REJECTED' ? 'red' : label === 'EXECUTED' ? 'green' : 'blue'
        return <Tag color={color}>{label === 'EXECUTED' ? '已执行' : label === 'WAITING_APPROVAL' ? '待审批' : label === 'REJECTED' ? '已拒绝' : v}</Tag>
      },
    },
    {
      title: '申请人', width: 110,
      render: (_, r) => r.requester ? `${r.requester.name}(${r.requester.department})` : '—',
    },
    {
      title: '创建时间', dataIndex: 'created_at', width: 150,
      render: (v) => (v || '').slice(0, 16).replace('T', ' '),
    },
    {
      title: '操作', key: 'op', width: 90,
      render: (_, r) => (
        <Button size="small" icon={<PlayCircleOutlined />} onClick={(e) => run(r, e)}>
          运行
        </Button>
      ),
    },
  ], [nav])

  return (
    <div className="page">
      <h1 className="page-title">工单列表</h1>
      <div className="page-sub">仿真运维工单 · 点击「运行」经 LangGraph 分诊并生成审计证据</div>

      <Space style={{ marginBottom: 14 }} wrap>
        <Segmented options={CATS} value={cat} onChange={setCat} />
        <Input.Search
          placeholder="搜索描述关键词"
          allowClear style={{ width: 260 }}
          onSearch={setQ}
        />
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>刷新</Button>
      </Space>

      <Table
        rowKey="ticket_id"
        size="middle"
        loading={loading}
        dataSource={data}
        columns={columns}
        pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
      />
    </div>
  )
}