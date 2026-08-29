import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import Landing from './pages/Landing'
import TicketList from './pages/TicketList'
import TicketDetail from './pages/TicketDetail'
import ApprovalFlow from './pages/ApprovalFlow'
import AuditLog from './pages/AuditLog'
import EvalReport from './pages/EvalReport'

const { Header, Content, Sider } = Layout

const MENU_ITEMS = [
  { key: '/app', label: '工单列表' },
  { key: '/app/approvals', label: '审批流程' },
  { key: '/app/audit', label: '审计日志' },
  { key: '/app/eval', label: '评测报告' },
]

function AppLayout() {
  const loc = useLocation()
  const nav = useNavigate()

  const active = (() => {
    const raw = loc.pathname
    // 两种路径都可能出现：/app/approvals  或  /approvals（嵌套路由下）
    const full = raw.startsWith('/app') ? raw : `/app${raw === '/' ? '' : raw}`
    // 详情页 /app/tickets/:id → 工单列表
    if (full.startsWith('/app/tickets')) return '/app'
    // 精确匹配优先
    for (const it of MENU_ITEMS) if (it.key === full) return it.key
    // 前缀匹配：/app/approvals/* → /app/approvals
    for (const it of MENU_ITEMS) if (it.key !== '/app' && full.startsWith(it.key + '/')) return it.key
    // 其余回落工单列表
    return '/app'
  })()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header>
        <div className="ops-header">
          <span className="ops-logo">OP</span>
          <span className="ops-brand">OpsPilot<small>可控执行的运维工单 Agent</small></span>
          <a
            onClick={(e) => { e.preventDefault(); nav('/') }}
            href="/"
            style={{ marginLeft: 'auto', color: '#fff', fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 6, textDecoration: 'none' }}
          >
            回到落地页
          </a>
        </div>
      </Header>
      <Layout>
        <Sider width={210}>
          <Menu
            mode="inline"
            selectedKeys={[active]}
            items={MENU_ITEMS}
            onClick={({ key }) => { if (key !== active) nav(key) }}
            style={{ borderRight: 0, background: 'transparent' }}
          />
        </Sider>
        <Layout style={{ background: 'var(--paper)' }}>
          <Content style={{ margin: 0 }}>
            <Routes>
              <Route index element={<TicketList />} />
              <Route path="tickets/:id" element={<TicketDetail />} />
              <Route path="approvals" element={<ApprovalFlow />} />
              <Route path="audit" element={<AuditLog />} />
              <Route path="eval" element={<EvalReport />} />
              <Route path="*" element={<Navigate to="/app" replace />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/app/*" element={<AppLayout />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}