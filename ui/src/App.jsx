import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout, Menu, Tag } from 'antd'
import {
  ProfileOutlined, AppstoreOutlined, AuditOutlined, CheckSquareOutlined, BarChartOutlined,
} from '@ant-design/icons'
import { Link, useLocation } from 'react-router-dom'
import TicketList from './pages/TicketList'
import TicketDetail from './pages/TicketDetail'
import ApprovalFlow from './pages/ApprovalFlow'
import AuditLog from './pages/AuditLog'
import EvalReport from './pages/EvalReport'

const { Header, Content, Sider } = Layout

const items = [
  { key: '/', icon: <AppstoreOutlined />, label: <Link to="/">工单列表</Link> },
  { key: '/approvals', icon: <CheckSquareOutlined />, label: <Link to="/approvals">审批流程</Link> },
  { key: '/audit', icon: <AuditOutlined />, label: <Link to="/audit">审计日志</Link> },
  { key: '/eval', icon: <BarChartOutlined />, label: <Link to="/eval">评测报告</Link> },
]

export default function App() {
  const loc = useLocation()
  const active = loc.pathname === '/' ? '/' : items
    .map((i) => i.key).find((k) => loc.pathname.startsWith(k)) || ''

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header>
        <div className="ops-header">
          <span className="ops-logo">OP</span>
          <span className="ops-brand">OpsPilot<small>可控执行的运维工单 Agent</small></span>
        </div>
      </Header>
      <Layout>
        <Sider width={210}>
          <Menu
            mode="inline"
            selectedKeys={[active]}
            items={items}
            style={{ borderRight: 0, background: 'transparent' }}
          />
        </Sider>
        <Layout style={{ background: 'var(--paper)' }}>
          <Content style={{ margin: 0 }}>
            <Routes>
              <Route path="/" element={<TicketList />} />
              <Route path="/tickets/:id" element={<TicketDetail />} />
              <Route path="/approvals" element={<ApprovalFlow />} />
              <Route path="/audit" element={<AuditLog />} />
              <Route path="/eval" element={<EvalReport />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  )
}