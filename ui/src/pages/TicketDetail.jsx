import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Row, Col, Card, Descriptions, Tag, Button, Space, Timeline,
  List, Steps, Alert, message, Spin,
} from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { api, RISK_COLOR, RISK_TEXT, INTENTS } from '../api'

const NODE_LABEL = {
  triage_agent: '分诊', ask_clarification: '澄清', retrieval_agent: '检索',
  action_agent: '行动计划', risk_router: '风险路由', tool_executor: '工具执行',
  final_response: '生成回复',
}

export default function TicketDetail() {
  const { id } = useParams()
  const [ticket, setTicket] = useState(null)
  const [running, setRunning] = useState(false)

  const load = async () => setTicket(await api.ticket(id))
  useEffect(() => { load() }, [id])

  const run = async () => {
    setRunning(true)
    try {
      await api.run(id)
      message.success('已运行，审计自动落盘')
      load()
    } finally {
      setRunning(false)
    }
  }

  if (!ticket) return <div className="page"><Spin /></div>

  const lastRun = ticket.last_run
  const steps = lastRun?.trace_steps || []

  return (
    <div className="page">
      <Space style={{ marginBottom: 16 }}>
        <Button onClick={() => window.history.back()}>← 返回</Button>
        <h1 className="page-title" style={{ fontSize: 18, margin: 0 }}>{ticket.ticket_id}</h1>
        <Tag color={RISK_COLOR[ticket.risk_level]}>风险 {RISK_TEXT[ticket.risk_level]}</Tag>
        <Tag>{INTENTS[ticket.category] || ticket.category}</Tag>
      </Space>

      <Row gutter={16}>
        <Col span={14}>
          <Card title="工单信息" extra={
            <Button type="primary" icon={<PlayCircleOutlined />} loading={running}
              onClick={run}>运行 Agent</Button>
          } style={{ marginBottom: 16 }}>
            <Descriptions column={2} size="middle">
              <Descriptions.Item label="描述" span={2}>{ticket.description}</Descriptions.Item>
              <Descriptions.Item label="申请人">
                {ticket.requester ? ticket.requester.name : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="部门">
                {ticket.requester?.department || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="优先级">{ticket.priority}</Descriptions.Item>
              <Descriptions.Item label="创建">{(ticket.created_at || '').slice(0, 16).replace('T', ' ')}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="Agent 执行轨迹（Trace）" style={{ marginBottom: 16 }}>
            {steps.length === 0 && <Alert type="info" message="尚未运行，点击「运行 Agent」生成可回放轨迹" />}
            <Steps
              direction="vertical"
              size="small"
              current={steps.length}
              items={steps.map((s) => ({
                title: NODE_LABEL[s.node] || s.node,
                description: (
                  <pre className="mono" style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                    {JSON.stringify(s.data)}
                  </pre>
                ),
              }))}
            />
          </Card>

          <Card title="消息流">
            {ticket.messages?.length === 0
              ? <Alert type="info" message="无补充消息" />
              : (
                <List
                  size="small"
                  dataSource={ticket.messages || []}
                  renderItem={(m) => (
                    <List.Item><span className="mono">[{m.created_at?.slice(0, 16).replace('T', ' ')}]</span> {m.content}</List.Item>
                  )}
                />
              )}
          </Card>
        </Col>

        <Col span={10}>
          {lastRun && (
            <Card title="运行结果" style={{ marginBottom: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Alert
                  type={lastRun.next_action === 'REJECTED' ? 'error' : lastRun.next_action === 'WAITING_APPROVAL' ? 'warning' : 'success'}
                  showIcon
                  banner
                  message={`终结态：${lastRun.next_action}`}
                  description={`意图 ${INTENTS[lastRun.intent] || lastRun.intent} · 风险 ${lastRun.risk_level} · 审批${lastRun.approval_required ? '需要' : '无需'}`}
                />
                <div><b>最终回复：</b></div>
                <pre className="mono" style={{ whiteSpace: 'pre-wrap', background: 'var(--paper)', padding: 10, borderRadius: 6 }}>{lastRun.final_answer}</pre>
              </Space>
            </Card>
          )}

          <Card title="工具计划（Action）" style={{ marginBottom: 16 }}>
            {(lastRun?.tool_plan || []).length === 0 && <Alert type="info" message="暂无工具计划" />}
            <List
              size="small"
              dataSource={lastRun?.tool_plan || []}
              renderItem={(t) => (
                <List.Item>
                  <Space>
                    <Tag color="blue">{t.tool}</Tag>
                    <span className="mono">{JSON.stringify(t.args)}</span>
                  </Space>
                </List.Item>
              )}
            />
          </Card>

          <Card title="检索证据（RAG）">
            {(lastRun?.retrieved_docs || []).length === 0 && <Alert type="info" message="本次未检索到知识库命中" />}
            <List
              size="small"
              dataSource={lastRun?.retrieved_docs || []}
              renderItem={(d) => (
                <List.Item><span className="mono">{d.source || d.document_id || d}: {JSON.stringify(d).slice(0, 120)}</span></List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}