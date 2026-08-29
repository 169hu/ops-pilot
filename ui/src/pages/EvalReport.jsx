import { useEffect, useState } from 'react'
import { Row, Col, Card, Tag, Table, Alert, Descriptions, Empty, Progress, Collapse } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { api, INTENTS } from '../api'

const METRIC_LABEL = {
  intent_accuracy: '意图准确率', risk_accuracy: '风险准确率',
  tool_selection_accuracy: '工具选择准确率', tool_param_accuracy: '工具参数准确率',
  final_status_accuracy: '终态准确率', rag_hit_rate: '知识库命中率',
}
const GATE_LABEL = {
  attack_intercept_rate: '攻击拦截率', forbidden_call_violations: '禁止工具违规',
  injection_block_rate: '注入拦截率', sensitive_block_rate: '敏感系统拦截率',
  unauthorized_block_rate: '越权拦截率',
}

export default function EvalReport() {
  const [rep, setRep] = useState(null)

  useEffect(() => { api.evalReport().then(setRep) }, [])

  if (!rep) return <div className="page"><Empty /></div>

  const m = rep.metrics || {}
  const g = rep.gates || {}
  const goldenCases = rep.detail?.golden?.cases || []
  const attackCases = rep.detail?.attacks?.cases || []
  const passed = Array.isArray(rep.passed) ? rep.passed[0] : rep.passed

  return (
    <div className="page">
      <h1 className="page-title">评测报告 · Eval 闭环</h1>
      <div className="page-sub">
        驱动 <Tag color="blue">{rep.driver}</Tag> 生成于 {rep.generated_at} ·
        红线门禁 <b style={{ color: passed ? '#5bb98c' : '#cf1322' }}>{passed ? '通过' : '失败'}</b>
      </div>

      {!passed && Array.isArray(rep.passed) && (
        <Alert
          type="error" showIcon style={{ marginBottom: 16 }}
          message="发布门禁未通过"
          description={rep.passed[1].join('；')}
        />
      )}

      <Row gutter={12} style={{ marginBottom: 16 }}>
        {Object.entries(METRIC_LABEL).map(([k, label]) => (
          <Col span={6} key={k}>
            <Card size="small" className="metric-card">
              <div style={{ color: '#8090a3', fontSize: 12 }}>{label}</div>
              <div className="value">{(m[k] * 100).toFixed(0)}%</div>
            </Card>
          </Col>
        ))}
      </Row>

      <Card title="红线门禁（发布前提 · 须 100%）" style={{ marginBottom: 16 }}>
        <Row gutter={[24, 8]}>
          {Object.entries(GATE_LABEL).map(([k, label]) => {
            const v = g[k]
            const ok = k === 'forbidden_call_violations' ? v === 0 : v >= 1
            return (
              <Col span={5} key={k}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  {ok ? <CheckCircleOutlined style={{ color: '#5bb98c' }} /> : <CloseCircleOutlined style={{ color: '#cf1322' }} />}
                  <span style={{ fontSize: 13 }}>{label}</span>
                </div>
                <Progress
                  percent={k === 'forbidden_call_violations' ? (v === 0 ? 100 : 0) : Math.round(v * 100)}
                  size="small"
                  status={ok ? 'success' : 'exception'}
                  format={() => (k === 'forbidden_call_violations' ? `${v} 次` : `${v * 100}%`)}
                />
              </Col>
            )
          })}
        </Row>
      </Card>

      <Row gutter={16}>
        <Col span={12}>
          <Card title={`能力评测 · golden（${goldenCases.length} 条）`} style={{ marginBottom: 16 }}>
            <Table
              size="small"
              rowKey="case_id"
              dataSource={goldenCases}
              pagination={{ pageSize: 10 }}
              columns={[
                { title: '用例', dataIndex: 'case_id', width: 100, render: (v) => <span className="mono">{v}</span> },
                { title: '意图', dataIndex: 'exp_intent', width: 110, render: (v) => <Tag>{INTENTS[v] || v}</Tag> },
                { title: '期望->实际', key: 'got', width: 170, render: (_, r) => `${r.exp_intent} → ${r.got_intent}` },
                { title: '结果', dataIndex: 'ok', width: 70, render: (ok) => ok
                  ? <Tag color="green">✓</Tag> : <Tag color="red">✗</Tag> },
              ]}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={`攻击红线 · attack（${attackCases.length} 条）`}>
            <Table
              size="small"
              rowKey="case_id"
              dataSource={attackCases}
              pagination={{ pageSize: 10 }}
              columns={[
                { title: '用例', dataIndex: 'case_id', width: 100, render: (v) => <span className="mono">{v}</span> },
                { title: '场景', dataIndex: 'name', ellipsis: true },
                { title: '攻击类型', dataIndex: 'attack_type', width: 150, render: (v) => <Tag color="volcano">{v}</Tag> },
                { title: '拦截', dataIndex: 'intercepted', width: 70, render: (ok) => ok
                  ? <Tag color="green">已拦截</Tag> : <Tag color="red">漏拦</Tag> },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}