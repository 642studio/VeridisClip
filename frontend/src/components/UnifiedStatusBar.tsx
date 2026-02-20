/**
 * 统一状态栏组件 - 替换旧的复杂进度系统
 * 支持下载中、处理中、完成等状态的统一显示
 */

import React, { useEffect, useState } from 'react'
import { Progress, Space, Typography, Tag } from 'antd'
import { 
  DownloadOutlined, 
  LoadingOutlined, 
  CheckCircleOutlined, 
  ExclamationCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import { useSimpleProgressStore, getStageDisplayName, getStageColor, isCompleted, isFailed } from '../stores/useSimpleProgressStore'

const { Text } = Typography

interface UnifiedStatusBarProps {
  projectId: string
  status: string
  downloadProgress?: number
  onStatusChange?: (status: string) => void
  onDownloadProgressUpdate?: (progress: number) => void
}

const translateDownloadMessage = (message: string): string => {
  if (!message) return ''
  const text = message.trim()
  if (text.includes('下载完成') && text.includes('准备开始处理')) return 'Descarga completa, preparando procesamiento...'
  if (text.includes('正在获取视频信息')) return 'Obteniendo informacion del video...'
  if (text.includes('正在下载视频')) return 'Descargando video...'
  if (text.includes('视频下载完成') && text.includes('处理字幕')) return 'Video descargado, procesando subtitulos...'
  if (text.includes('正在使用Whisper生成字幕')) return 'Generando subtitulos con Whisper...'
  if (text.includes('字幕生成完成')) return 'Subtitulos generados, preparando procesamiento...'
  if (text.includes('下载失败')) return 'Error de descarga'
  return text
}

const getProcessingFallbackMessage = (message: string): string => {
  if (!message) return 'Procesando pipeline...'
  if (message.toLowerCase().includes('descarga completa')) return 'Iniciando pipeline...'
  return message
}

export const UnifiedStatusBar: React.FC<UnifiedStatusBarProps> = ({
  projectId,
  status,
  downloadProgress = 0,
  onStatusChange,
  onDownloadProgressUpdate
}) => {
  const { getProgress, startPolling, stopPolling } = useSimpleProgressStore()
  const [isPolling, setIsPolling] = useState(false)
  const [currentDownloadProgress, setCurrentDownloadProgress] = useState(downloadProgress)
  const [currentDownloadMessage, setCurrentDownloadMessage] = useState('')
  
  const progress = getProgress(projectId)

  useEffect(() => {
    setCurrentDownloadProgress(downloadProgress)
  }, [downloadProgress])

  // 根据状态决定是否轮询
  useEffect(() => {
    if ((status === 'processing' || status === 'pending') && !isPolling) {
      console.log(`开始轮询处理进度: ${projectId}`)
      startPolling([projectId], 2000)
      setIsPolling(true)
    } else if (status !== 'processing' && status !== 'pending' && isPolling) {
      console.log(`停止轮询处理进度: ${projectId}`)
      stopPolling()
      setIsPolling(false)
    }

    return () => {
      if (isPolling) {
        console.log(`清理轮询: ${projectId}`)
        stopPolling()
        setIsPolling(false)
      }
    }
  }, [status, projectId, isPolling, startPolling, stopPolling])

  // 下载进度轮询
  useEffect(() => {
    if (status === 'downloading' || status === 'importing' || status === 'processing') {
      const pollDownloadProgress = async () => {
        try {
          console.log(`轮询下载进度: ${projectId}`)
          const response = await fetch(`http://localhost:8000/api/v1/projects/${projectId}`)
          if (response.ok) {
            const projectData = await response.json()
            console.log('项目数据:', projectData)
            const processingConfig = projectData.processing_config || projectData.settings || {}
            const newProgress = processingConfig.download_progress || 0
            const newMessage = translateDownloadMessage(processingConfig.download_message || '')
            if (newProgress > 0 || newMessage) {
              console.log(`下载进度更新: ${newProgress}%`)
              setCurrentDownloadProgress(newProgress)
              setCurrentDownloadMessage(newMessage)
              onDownloadProgressUpdate?.(newProgress)
            }
            
            // 按后端真实状态切换卡片状态
            if (projectData.status === 'processing') {
              onStatusChange?.('processing')
            } else if (projectData.status === 'failed' || projectData.status === 'error') {
              onStatusChange?.('failed')
            } else if (projectData.status === 'completed') {
              onStatusChange?.('completed')
            } else if (newProgress >= 100 && status === 'downloading') {
              // 兼容旧路径：下载完成后进入处理中
              setTimeout(() => {
                onStatusChange?.('processing')
              }, 1000)
            }
          } else {
            console.error('获取项目数据失败:', response.status, response.statusText)
          }
        } catch (error) {
          console.error('获取下载进度失败:', error)
        }
      }

      // 立即获取一次
      pollDownloadProgress()
      
      // 每2秒轮询一次
      const interval = setInterval(pollDownloadProgress, 2000)
      
      return () => clearInterval(interval)
    }
  }, [status, projectId, onDownloadProgressUpdate, onStatusChange])

  // 处理状态变化
  useEffect(() => {
    if (progress && onStatusChange) {
      if (isCompleted(progress.stage)) {
        onStatusChange('completed')
      } else if (isFailed(progress.message)) {
        onStatusChange('failed')
      }
    }
  }, [progress, onStatusChange])

  // 导入中状态
  if (status === 'importing') {
    return (
      <div style={{
        background: 'rgba(255, 193, 7, 0.1)',
        border: '1px solid rgba(255, 193, 7, 0.3)',
        borderRadius: '3px',
        padding: '3px 6px',
        textAlign: 'center',
        width: '100%'
      }}>
        <div style={{ 
          color: '#ffc107',
          fontSize: '11px', 
          fontWeight: 600, 
          lineHeight: '12px'
        }}>
          {Math.round(currentDownloadProgress)}%
        </div>
        <div style={{ 
          color: '#999999', 
          fontSize: '8px', 
          lineHeight: '9px'
        }}>
          {currentDownloadMessage ? 'Procesando importacion' : 'Importando'}
        </div>
      </div>
    )
  }

  // 下载中状态
  if (status === 'downloading') {
    return (
      <div style={{
        background: 'rgba(24, 144, 255, 0.1)',
        border: '1px solid rgba(24, 144, 255, 0.3)',
        borderRadius: '3px',
        padding: '3px 6px',
        textAlign: 'center',
        width: '100%'
      }}>
        <div style={{ 
          color: '#1890ff',
          fontSize: '11px', 
          fontWeight: 600, 
          lineHeight: '12px'
        }}>
          {Math.round(currentDownloadProgress)}%
        </div>
        <div style={{ 
          color: '#999999', 
          fontSize: '8px', 
          lineHeight: '9px'
        }}>
          Descargando
        </div>
      </div>
    )
  }

  // 处理中状态 - 使用新的简化进度系统
  if (status === 'processing') {
    if (!progress) {
      const processingPercent = currentDownloadProgress >= 100 ? 95 : currentDownloadProgress
      // 等待进度数据
      return (
      <div style={{
        background: 'rgba(82, 196, 26, 0.1)',
        border: '1px solid rgba(82, 196, 26, 0.3)',
        borderRadius: '3px',
        padding: '3px 6px',
        textAlign: 'center',
        width: '100%'
      }}>
        <div style={{ 
          color: '#52c41a',
          fontSize: '11px', 
          fontWeight: 600, 
          lineHeight: '12px'
        }}>
          {Math.round(processingPercent)}%
        </div>
        <div style={{ 
          color: '#999999', 
          fontSize: '8px', 
          lineHeight: '9px'
        }}>
          {getProcessingFallbackMessage(currentDownloadMessage)}
        </div>
      </div>
      )
    }

    const { stage, percent, message } = progress
    const stageDisplayName = getStageDisplayName(stage)
    const stageColor = getStageColor(stage)
    const failed = isFailed(message)

    return (
      <div style={{
        background: failed 
          ? 'rgba(255, 77, 79, 0.1)'
          : 'rgba(82, 196, 26, 0.1)',
        border: failed 
          ? '1px solid rgba(255, 77, 79, 0.3)'
          : '1px solid rgba(82, 196, 26, 0.3)',
        borderRadius: '3px',
        padding: '3px 6px',
        textAlign: 'center',
        width: '100%'
      }}>
        <div style={{ 
          color: failed ? '#ff4d4f' : '#52c41a',
          fontSize: '11px', 
          fontWeight: 600, 
          lineHeight: '12px'
        }}>
          {failed ? '✗ Error' : `${percent}%`}
        </div>
        <div style={{ 
          color: '#999999', 
          fontSize: '8px', 
          lineHeight: '9px',
          minHeight: '9px' // 确保失败状态也有固定高度
        }}>
          {failed ? '' : stageDisplayName}
        </div>
      </div>
    )
  }

  // 已完成状态
  if (status === 'completed') {
    return (
      <div style={{
        background: 'rgba(82, 196, 26, 0.1)',
        border: '1px solid rgba(82, 196, 26, 0.3)',
        borderRadius: '3px',
        padding: '3px 6px',
        textAlign: 'center',
        width: '100%'
      }}>
        <div style={{ 
          color: '#52c41a',
          fontSize: '11px', 
          fontWeight: 600, 
          lineHeight: '12px'
        }}>
          ✓
        </div>
        <div style={{ 
          color: '#999999', 
          fontSize: '8px', 
          lineHeight: '9px'
        }}>
          Completado
        </div>
      </div>
    )
  }

  // 失败状态
  if (status === 'failed') {
    return (
      <div style={{
        background: 'rgba(255, 77, 79, 0.1)',
        border: '1px solid rgba(255, 77, 79, 0.3)',
        borderRadius: '3px',
        padding: '3px 6px',
        textAlign: 'center',
        width: '100%'
      }}>
        <div style={{ 
          color: '#ff4d4f',
          fontSize: '11px', 
          fontWeight: 600, 
          lineHeight: '12px'
        }}>
          ✗ Error
        </div>
        <div style={{ 
          color: '#999999', 
          fontSize: '8px', 
          lineHeight: '9px',
          minHeight: '9px' // 确保失败状态也有固定高度
        }}>
          Fallo de procesamiento
        </div>
      </div>
    )
  }

  // 等待状态
  return (
    <div style={{
      background: 'rgba(217, 217, 217, 0.1)',
      border: '1px solid rgba(217, 217, 217, 0.3)',
      borderRadius: '3px',
      padding: '3px 6px',
      textAlign: 'center',
      width: '100%'
    }}>
      <div style={{ 
        color: '#d9d9d9',
        fontSize: '11px', 
        fontWeight: 600, 
        lineHeight: '12px'
      }}>
        ○ En espera
      </div>
      <div style={{ 
        color: '#999999', 
        fontSize: '8px', 
        lineHeight: '9px',
        minHeight: '9px' // 确保等待状态也有固定高度
      }}>
        Esperando proceso
      </div>
    </div>
  )
}

// 简化的进度条组件 - 用于详细进度显示
interface SimpleProgressDisplayProps {
  projectId: string
  status: string
  showDetails?: boolean
}

export const SimpleProgressDisplay: React.FC<SimpleProgressDisplayProps> = ({
  projectId,
  status,
  showDetails = false
}) => {
  const { getProgress } = useSimpleProgressStore()
  const progress = getProgress(projectId)

  if (status !== 'processing' || !progress || !showDetails) {
    return null
  }

  const { stage, percent, message } = progress
  const stageDisplayName = getStageDisplayName(stage)
  const stageColor = getStageColor(stage)

  return (
    <div style={{ marginTop: '8px' }}>
      <Progress
        percent={percent}
        strokeColor={stageColor}
        showInfo={true}
        size="small"
        format={(percent) => `${percent}%`}
      />
      {message && (
        <Text type="secondary" style={{ fontSize: '11px', display: 'block', marginTop: '4px' }}>
          {message}
        </Text>
      )}
    </div>
  )
}
