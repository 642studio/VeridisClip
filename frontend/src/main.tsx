import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import esES from 'antd/locale/es_ES'
import dayjs from 'dayjs'
import 'dayjs/locale/es'
import relativeTime from 'dayjs/plugin/relativeTime'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import App from './App.tsx'
import './index.css'

// Dayjs plugins
dayjs.extend(relativeTime)
dayjs.extend(timezone)
dayjs.extend(utc)

// Localizacion en espanol
dayjs.locale('es')
dayjs.tz.setDefault('America/Hermosillo')

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ConfigProvider locale={esES}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </ConfigProvider>,
)
