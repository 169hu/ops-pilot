import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

const FEATURES = [
  {
    title: '可控执行 · Tool Gateway',
    desc: '每一工具调用先过安全网关：注入识别、敏感系统/生产库拦截、越权校验、批量风险阻断，红线一票否决。',
  },
  {
    title: '全程可观测 · Trace',
    desc: '工单从分诊到执行的每一步都有迹可循：工具调用计划、RAG 检索证据、风险路由与审计证据链完整留痕。',
  },
  {
    title: '自动评测 · Eval',
    desc: 'golden 能力指标 + 攻击红线门禁双通道，发布前硬门槛校验，保证每次改动都能被量化验证。',
  },
  {
    title: '双引擎驱动',
    desc: '内置确定性规则引擎可离线复现基线；接入 DeepSeek 真实大模型后升级为生产级意图理解。',
  },
  {
    title: '审批闭环',
    desc: '高/中危操作进入审批流，主管审批通过后授权才真正落地执行并记录审计日志。',
  },
  {
    title: '一键部署',
    desc: 'Docker Compose 编排前端 + 后端 + 数据生成，健康检查与离线模式开箱即用。',
  },
]

const STACK = [
  'React + AntD', 'FastAPI', 'LangGraph', 'Tool Gateway',
  'RAG 检索', '审计日志', '自动评测', 'Docker Compose',
]

export default function Landing() {
  const nav = useNavigate()
  const wrapRef = useRef(null)
  const boardRef = useRef(null)
  const spotlightRef = useRef(null)

  useEffect(() => {
    const wrap = wrapRef.current
    const board = boardRef.current
    if (!wrap || !board) return

    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    const size = () => { canvas.width = wrap.clientWidth; canvas.height = wrap.clientHeight }
    size()
    board.appendChild(canvas)

    const draw = (x, y, r) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const grad = ctx.createRadialGradient(x, y, 0, x, y, r)
      grad.addColorStop(0, 'rgba(31, 62, 110, 0.42)')
      grad.addColorStop(0.45, 'rgba(31, 62, 110, 0.16)')
      grad.addColorStop(1, 'rgba(31, 62, 110, 0)')
      ctx.fillStyle = grad
      ctx.fillRect(0, 0, canvas.width, canvas.height)
    }

    const update = (e) => {
      const rect = wrap.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      const r = Math.min(340, rect.width * 0.28)
      draw(x, y, r)
      if (spotlightRef.current) {
        spotlightRef.current.style.left = `${x}px`
        spotlightRef.current.style.top = `${y}px`
        spotlightRef.current.style.opacity = 1
      }
    }

    let raf = 0
    wrap.addEventListener('pointermove', (e) => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => update(e))
    })
    wrap.addEventListener('pointerleave', () => {
      cancelAnimationFrame(raf)
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      if (spotlightRef.current) spotlightRef.current.style.opacity = 0
    })

    window.addEventListener('resize', size)
    return () => { window.removeEventListener('resize', size) }
  }, [])

  return (
    <div className="landing">
      {/* Top bar */}
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <div className="landing-logo">
            <span className="ops-logo">OP</span>
            <span className="landing-brand">OpsPilot</span>
          </div>
          <div className="landing-nav-links">
            <a href="#features">特性</a>
            <a href="#stack">技术栈</a>
            <a href="#cta">部署</a>
          </div>
          <button className="landing-cta nav" onClick={() => nav('/app')}>
            进入控制台
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section ref={wrapRef} className="landing-hero" id="top">
        <div ref={boardRef} className="spotlight-board" aria-hidden="true" />
        <div ref={spotlightRef} className="spotlight-cursor" aria-hidden="true" />

        <div className="landing-hero-content">
          <div className="landing-badge">企业运维 · 受控执行平台</div>
          <h1 className="landing-title">
            让每个运维操作<br />都在<b>安全围栏</b>内执行
          </h1>
          <p className="landing-desc">
            OpsPilot 是一个面向企业 IT 运维的工单 Agent —— 用自然语言分诊、
            检索证据、拟定工具计划，并以 <b>Tool Gateway</b> 守护每一次可控执行。
            从咨询解答到权限审批，全程留痕、可评测、可部署。
          </p>
          <div className="landing-actions">
            <button className="landing-cta primary" onClick={() => nav('/app')}>
              打开控制台 Demo
            </button>
            <button className="landing-cta ghost" onClick={() => nav('/app/eval')}>
              查看评测报告
            </button>
          </div>
          <div className="landing-metrics">
            <div><b>红线拦截</b><span>100%</span></div>
            <div><b>可控工具</b><span>受控执行</span></div>
            <div><b>审计记录</b><span>全链路</span></div>
          </div>
        </div>

        <div className="landing-scroll" aria-hidden="true">▾</div>
      </section>

      {/* Features */}
      <section className="landing-section" id="features">
        <h2 className="landing-section-title">它解决了什么问题</h2>
        <p className="landing-section-sub">从「能回答问题」到「能安全地替人干活」</p>
        <div className="landing-grid">
          {FEATURES.map((f) => (
            <div className="landing-feature" key={f.title}>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Stack */}
      <section className="landing-section landing-dim" id="stack">
        <h2 className="landing-section-title">技术栈</h2>
        <p className="landing-section-sub">一套完整的前后端 + Agent + 评测 + 部署链路</p>
        <div className="landing-stack">
          {STACK.map((s) => <span key={s}>{s}</span>)}
        </div>
      </section>

      {/* CTA */}
      <section className="landing-cta-band" id="cta">
        <h2>把它交给你自己的运维团队，十秒上手</h2>
        <p>Docker Compose 一条命令启动真实大模型驱动的受控 Agent 平台。</p>
        <button className="landing-cta primary large" onClick={() => nav('/app')}>
          进入控制台
        </button>
      </section>

      <footer className="landing-footer">
        <span>OpsPilot · 可控执行的运维工单 Agent Demo</span>
        <span className="landing-footer-tags">
          <span>Tool Gateway</span><span className="sep">·</span>
          <span>Trace 可观测</span><span className="sep">·</span>
          <span>Eval 自动评测</span>
        </span>
      </footer>
    </div>
  )
}