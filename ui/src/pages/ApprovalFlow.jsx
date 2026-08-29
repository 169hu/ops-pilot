import { useEffect, useState } from 'react'
import { Card, Table, Tag, Button, Space, message, Popconfirm, Empty, Tooltip } from 'antd'
import { CheckOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api, RISK_COLOR, RISK_TEXT, INTENTS } from '../api'

export default function ApprovalFlow() {
  const nav = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [acting, setActing] = useState('')

  const load = async () => {
    setLoading(true)
    try { setItems((await api.approvals()).items) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const approve = async (id) => {
    setActing(id)
    try {
      await api.approve(id)
      message.success(`已批准 ${id}，授权落地`)
      load()
    } finally { setActing('') }
  }

  const columns = [
    {
      title: '工单号', dataIndex: 'ticket_id', width: 100, render: (v) => <span className="mono">{v}</span>,
    },
    {
      title: '标题', dataIndex: 'title', width: 180,
      render: (v, r) => <Button type="link" style={{ padding: 0 }} onClick={() => nav(`/tickets/${r.ticket_id}`)}>{v}</Button>,
    },
    { title: '分类', dataIndex: 'intent', width: 120, render: (v) => <Tag>{INTENTS[v] || v}</Tag> },
    { title: '风险', dataIndex: 'risk_level', width: 80, render: (v) => <Tag color={RISK_COLOR[v]}>{RISK_TEXT[v]}</Tag> },
    {
      title: '待授权工具', dataIndex: 'pending_tools', width: 200,
      render: (arr) => (arr || []).length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} /> : arr.map((t) => <Tag key={t} color="gold">{t}</Tag>),
    },
    {
      title: '审批动作', key: 'op', width: 140,
      render: (_, r) => (
        <Popconfirm title={`确认批准 ${r.ticket_id}？`} onConfirm={() => approve(r.ticket_id)}>
          <Button
            type="primary" icon={<CheckOutlined />} size="small"
            loading={acting === r.ticket_id}
          >批准并执行</Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <div className="page">
      <h1 className="page-title">审批流程</h1>
      <div className="page-sub">等待 IT 审批的高风险 / 授权变更 · 批准后经 Tool Gateway 实名落盘审计</div>
      <Space style={{ marginBottom: 14 }}><Button icon={<ReloadOutlined />} onClick={load} loading={loading}>刷新</Button></Space>

      <Card title={`待审批（${items.length}）`}>
        {items.length === 0 ? (
          <Empty description="暂无待审批工单，从「工单列表」运行权限类工单即可进入该队列" />
        ) : (
          <Table rowKey="ticket_id" size="middle" dataSource={items} columns={columns} pagination={false} />
        )}
      </Card>

      <Card title="审批口径" style={{ marginTop: 16 }}>
        <ul>
          <li><b>grant_permission</b> 为变更操作，恒需审批；命中生产库 / admin / root 自动升级为高风险。</li>
          <li>审批通过后重放 Agent 图，授权经 Tool Gateway 落地并写入 <span className="mono">tool_invocations</span> 审计。</li>
          <li>低风险只读工具（检索/状态/知识库）自动执行，无需进入本队列。</li>
        </ul>
      </Card>
    </div>
  )
}