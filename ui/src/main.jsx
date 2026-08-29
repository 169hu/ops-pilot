import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './styles.css'

const brand = {
  colorPrimary: '#1F3E6E',
  borderRadius: 6,
  fontFamily: '"PingFang SC", "Microsoft YaHei", "Source Han Sans SC", sans-serif',
  colorBgLayout: '#F6F4EF',
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: brand,
        algorithm: theme.defaultAlgorithm,
        components: {
          Layout: { headerBg: '#1F3E6E', siderBg: '#F6F4EF', headerHeight: 56 },
          Menu: {
            itemBg: 'transparent',
            itemSelectedBg: 'rgba(31, 62, 110, 0.10)',
            itemSelectedColor: '#1F3E6E',
            itemHoverBg: 'rgba(31, 62, 110, 0.06)',
            itemHoverColor: '#1F3E6E',
          },
          Card: { headerBg: '#FFFFFF' },
        },
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>,
)