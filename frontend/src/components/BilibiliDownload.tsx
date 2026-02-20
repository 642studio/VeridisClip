import React, { useState, useEffect } from 'react'
import { Button, message, Progress, Input, Card, Typography, Space, Spin, Select } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { projectApi, bilibiliApi, VideoCategory, BilibiliDownloadTask } from '../services/api'
import { useProjectStore } from '../store/useProjectStore'

const { Text } = Typography

interface BilibiliDownloadProps {
  onDownloadSuccess?: (projectId: string) => void
}

// 使用从API导入的BilibiliDownloadTask类型

const BilibiliDownload: React.FC<BilibiliDownloadProps> = ({ onDownloadSuccess }) => {
  const [url, setUrl] = useState('')
  const [projectName, setProjectName] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedBrowser, setSelectedBrowser] = useState<string>('')
  const [categories, setCategories] = useState<VideoCategory[]>([])
  const [loadingCategories, setLoadingCategories] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [currentTask, setCurrentTask] = useState<BilibiliDownloadTask | null>(null)
  const [pollingInterval, setPollingInterval] = useState<number | null>(null)
  const [videoInfo, setVideoInfo] = useState<any>(null)
  const [parsing, setParsing] = useState(false)
  const [error, setError] = useState('')
  
  const { addProject } = useProjectStore()

  // 加载Categoria de video配置
  useEffect(() => {
    const loadCategories = async () => {
      setLoadingCategories(true)
      try {
        const response = await projectApi.getVideoCategories()
        setCategories(response.categories)
        if (response.default_category) {
          setSelectedCategory(response.default_category)
        } else if (response.categories.length > 0) {
          setSelectedCategory(response.categories[0].value)
        }
      } catch (error) {
        console.error('Failed to load video categories:', error)
        message.error('Error al cargar categorias de video')
      } finally {
        setLoadingCategories(false)
      }
    }

    loadCategories()
  }, [])

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [pollingInterval])

  const validateVideoUrl = (url: string): boolean => {
    const bilibiliPatterns = [
      /^https?:\/\/www\.bilibili\.com\/video\/[Bb][Vv][0-9A-Za-z]+/,
      /^https?:\/\/bilibili\.com\/video\/[Bb][Vv][0-9A-Za-z]+/,
      /^https?:\/\/b23\.tv\/[0-9A-Za-z]+/,
      /^https?:\/\/www\.bilibili\.com\/video\/av\d+/,
      /^https?:\/\/bilibili\.com\/video\/av\d+/
    ]
    
    const youtubePatterns = [
      /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[a-zA-Z0-9_-]+/,
      /^https?:\/\/youtu\.be\/[a-zA-Z0-9_-]+/,
      /^https?:\/\/(www\.)?youtube\.com\/embed\/[a-zA-Z0-9_-]+/,
      /^https?:\/\/(www\.)?youtube\.com\/v\/[a-zA-Z0-9_-]+/
    ]

    const facebookPatterns = [
      /^https?:\/\/(www\.)?facebook\.com\/.+/i,
      /^https?:\/\/fb\.watch\/.+/i,
      /^https?:\/\/m\.facebook\.com\/.+/i
    ]
    
    return bilibiliPatterns.some(pattern => pattern.test(url)) || 
           youtubePatterns.some(pattern => pattern.test(url)) ||
           facebookPatterns.some(pattern => pattern.test(url))
  }
  
  const getVideoType = (url: string): 'bilibili' | 'youtube' | 'facebook' | null => {
    const bilibiliPatterns = [
      /^https?:\/\/www\.bilibili\.com\/video\/[Bb][Vv][0-9A-Za-z]+/,
      /^https?:\/\/bilibili\.com\/video\/[Bb][Vv][0-9A-Za-z]+/,
      /^https?:\/\/b23\.tv\/[0-9A-Za-z]+/,
      /^https?:\/\/www\.bilibili\.com\/video\/av\d+/,
      /^https?:\/\/bilibili\.com\/video\/av\d+/
    ]
    
    const youtubePatterns = [
      /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[a-zA-Z0-9_-]+/,
      /^https?:\/\/youtu\.be\/[a-zA-Z0-9_-]+/,
      /^https?:\/\/(www\.)?youtube\.com\/embed\/[a-zA-Z0-9_-]+/,
      /^https?:\/\/(www\.)?youtube\.com\/v\/[a-zA-Z0-9_-]+/
    ]

    const facebookPatterns = [
      /^https?:\/\/(www\.)?facebook\.com\/.+/i,
      /^https?:\/\/fb\.watch\/.+/i,
      /^https?:\/\/m\.facebook\.com\/.+/i
    ]
    
    if (bilibiliPatterns.some(pattern => pattern.test(url))) {
      return 'bilibili'
    } else if (youtubePatterns.some(pattern => pattern.test(url))) {
      return 'youtube'
    } else if (facebookPatterns.some(pattern => pattern.test(url))) {
      return 'facebook'
    }
    return null
  }

  const parseVideoInfo = async () => {
    if (!url.trim()) {
      setError('Ingresa un enlace de video valido')
      return
    }

    const videoType = getVideoType(url.trim())
    if (!videoType) {
      setError('Ingresa un enlace valido de Bilibili, YouTube o Facebook')
      return
    }

    setParsing(true)
    setError('') // 清除之前的错误信息
    
    try {
      let response
      if (videoType === 'bilibili') {
        response = await bilibiliApi.parseVideoInfo(url.trim(), selectedBrowser)
      } else if (videoType === 'youtube' || videoType === 'facebook') {
        response = await bilibiliApi.parseYouTubeVideoInfo(url.trim(), selectedBrowser)
      }
      
      const parsedVideoInfo = response.video_info
      
      setVideoInfo(parsedVideoInfo)
      setError('') // 解析成功，清除错误信息
      
      // 自动填充Nombre del proyecto
      if (!projectName && parsedVideoInfo.title) {
        setProjectName(parsedVideoInfo.title)
      }
      
      return parsedVideoInfo
    } catch (error: any) {
      setError('Ingresa un enlace de video valido')
      setVideoInfo(null)
    } finally {
      setParsing(false)
    }
  }

  const startPolling = (taskId: string, videoType: 'bilibili' | 'youtube' | 'facebook') => {
    const interval = setInterval(async () => {
      try {
        let task
        if (videoType === 'bilibili') {
          task = await bilibiliApi.getTaskStatus(taskId)
        } else {
          task = await bilibiliApi.getYouTubeTaskStatus(taskId)
        }
        setCurrentTask(task)
        
        if (task.status === 'completed') {
          clearInterval(interval)
          setPollingInterval(null)
          setDownloading(false)
          message.success('Descarga de video completada')
          
          if (task.project_id && onDownloadSuccess) {
            onDownloadSuccess(task.project_id)
          }
          
          // 重置状态
          resetForm()
        } else if (task.status === 'failed') {
          clearInterval(interval)
          setPollingInterval(null)
          setDownloading(false)
          message.error(`Descarga fallida: ${task.error_message || 'error desconocido'}`)
          resetForm()
        }
      } catch (error) {
        console.error('Error al consultar estado de tarea:', error)
      }
    }, 2000)
    
    setPollingInterval(interval)
  }

  const handleDownload = async () => {
    if (!url.trim()) {
      message.error('Ingresa el enlace del video')
      return
    }

    const videoType = getVideoType(url.trim())
    if (!videoType) {
      message.error('Ingresa un enlace valido de Bilibili, YouTube o Facebook')
      return
    }

    setDownloading(true)
    
    try {
      const requestBody: any = {
        url: url.trim(),
        video_category: selectedCategory
      }
      
      if (projectName.trim()) {
        requestBody.project_name = projectName.trim()
      }
      
      if (selectedBrowser) {
        requestBody.browser = selectedBrowser
      }

      let response
      if (videoType === 'bilibili') {
        response = await bilibiliApi.createDownloadTask(requestBody)
      } else {
        response = await bilibiliApi.createYouTubeDownloadTask(requestBody)
      }
      
      // 检查响应是否包含项目ID（新的优化后的响应格式）
      if (response.project_id) {
        // 新格式：项目已创建，立即重置表单
        setCurrentTask(null)
        setDownloading(false)
        resetForm()
        
        // 显示统一的成功提示
        const platformName = videoType === 'bilibili' ? 'Bilibili' : (videoType === 'facebook' ? 'Facebook' : 'YouTube')
        message.success(`${platformName} proyecto creado. La descarga continua en segundo plano; puedes agregar mas proyectos.`)
        
        if (onDownloadSuccess) {
          onDownloadSuccess(response.project_id)
        }
      } else {
        // 旧格式：继续轮询任务状态
        setCurrentTask(response)
        startPolling(response.id, videoType)
      }
      
    } catch (error: any) {
      setDownloading(false)
      const errorMessage = error.response?.data?.detail || error.message || 'Error al crear tarea de descarga'
      message.error(errorMessage)
    }
  }

  const resetForm = () => {
    setUrl('')
    setProjectName('')
    setCurrentTask(null)
    setVideoInfo(null)
    setError('')
    // 保持分类和浏览器选择，方便用户继续添加项目
    // setSelectedCategory(categories[0].value)
    // setSelectedBrowser('')
  }

  const stopDownload = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      setPollingInterval(null)
    }
    setDownloading(false)
    setCurrentTask(null)
    message.info('Se detuvo el monitoreo de la descarga')
  }

  return (
    <div style={{
      width: '100%',
      margin: '0 auto'
    }}>

      {/* 输入表单 */}
      <div style={{ marginBottom: '16px' }}>
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <div>
            <Input.TextArea
              placeholder="Pega un enlace de Bilibili, YouTube o Facebook. Ejemplos: Bilibili: https://www.bilibili.com/video/BV1xx411c7mu, YouTube: https://www.youtube.com/watch?v=xxxxx, Facebook: https://www.facebook.com/.../videos/..."
              value={url}
              onChange={(e) => {
                setUrl(e.target.value)
                // 清除之前的解析结果和错误信息
                if (videoInfo) {
                  setVideoInfo(null)
                  setProjectName('')
                }
                if (error) {
                  setError('')
                }
              }}
              onBlur={() => {
                // 失去焦点时自动解析
                if (url.trim() && !videoInfo && validateVideoUrl(url.trim())) {
                  parseVideoInfo();
                }
              }}
              style={{
                background: 'rgba(38, 38, 38, 0.8)',
                border: '1px solid rgba(79, 172, 254, 0.3)',
                borderRadius: '8px',
                color: '#ffffff',
                fontSize: '14px',
                resize: 'none'
              }}
              rows={2}
              disabled={downloading || parsing}
            />
            {parsing && (
               <div style={{
                 marginTop: '8px',
                 color: '#4facfe',
                 fontSize: '14px',
                 display: 'flex',
                 alignItems: 'center',
                 gap: '8px'
               }}>
                 <span>Analizando informacion del video...</span>
               </div>
             )}
             {error && !parsing && (
               <div style={{
                 marginTop: '8px',
                 color: '#ff6b6b',
                 fontSize: '14px',
                 display: 'flex',
                 alignItems: 'center',
                 gap: '8px'
               }}>
                 <span>{error}</span>
               </div>
             )}
          </div>
          
          {/* 显示解析成功的视频信息 */}
          {videoInfo && (
            <div style={{
              background: 'rgba(102, 126, 234, 0.1)',
              border: '1px solid rgba(102, 126, 234, 0.3)',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '12px'
            }}>
              <Text style={{ color: '#667eea', fontWeight: 600, fontSize: '16px', display: 'block', marginBottom: '8px' }}>
                Informacion del video analizada correctamente
              </Text>
              <Text style={{ color: '#ffffff', fontSize: '14px', display: 'block' }}>
                {videoInfo.title}
              </Text>
              <Text style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: '12px' }}>
                {getVideoType(url) === 'bilibili' ? 'Creador' : 'Canal'}: {videoInfo.uploader || 'Desconocido'} • Duracion: {videoInfo.duration ? `${Math.floor(videoInfo.duration / 60)}:${String(Math.floor(videoInfo.duration % 60)).padStart(2, '0')}` : 'Desconocido'}
              </Text>
            </div>
          )}
          
          {/* 只有解析成功后才显示Nombre del proyecto和分类 */}
          {videoInfo && (
            <>
              <div>
                <Text style={{ color: '#ffffff', marginBottom: '12px', display: 'block', fontSize: '16px', fontWeight: 500 }}>Nombre del proyecto (opcional)</Text>
                <Input
                  placeholder="Si lo dejas vacio, se usara el titulo del video como nombre del proyecto"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  style={{
                    background: 'rgba(38, 38, 38, 0.8)',
                    border: '1px solid rgba(79, 172, 254, 0.3)',
                    borderRadius: '12px',
                    color: '#ffffff',
                    height: '48px',
                    fontSize: '14px'
                  }}
                  disabled={downloading}
                />
              </div>
              
              <div>
                <Text style={{ color: '#ffffff', marginBottom: '12px', display: 'block', fontSize: '16px', fontWeight: 500 }}>Seleccion de navegador (necesaria para subtitulos AI)</Text>
                <Select
                  placeholder="Selecciona navegador para usar cookies (opcional)"
                  value={selectedBrowser || undefined}
                  onChange={(value) => setSelectedBrowser(value || '')}
                  allowClear
                  style={{
                    width: '100%',
                    height: '48px'
                  }}
                  dropdownStyle={{
                    background: 'rgba(38, 38, 38, 0.95)',
                    border: '1px solid rgba(79, 172, 254, 0.3)',
                    borderRadius: '12px'
                  }}
                  disabled={downloading}
                >
                  <Select.Option value="chrome">Chrome</Select.Option>
                  <Select.Option value="firefox">Firefox</Select.Option>
                  <Select.Option value="safari">Safari</Select.Option>
                  <Select.Option value="edge">Edge</Select.Option>
                </Select>
                <Text style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: '12px', marginTop: '8px', display: 'block' }}>
                  Seleccionar navegador permite usar sesion iniciada para bajar subtitulos IA. Si no seleccionas, solo se descargaran subtitulos publicos.
                </Text>
              </div>
              
              <div>
                <Text style={{ color: '#ffffff', marginBottom: '12px', display: 'block', fontSize: '16px', fontWeight: 500 }}>Categoria de video</Text>
                {loadingCategories ? (
                  <Spin size="small" />
                ) : (
                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '8px'
                  }}>
                    {categories.map(category => {
                      const isSelected = selectedCategory === category.value
                      return (
                        <div
                          key={category.value}
                          onClick={() => setSelectedCategory(category.value)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: isSelected 
                              ? `2px solid ${category.color}` 
                              : '2px solid rgba(255, 255, 255, 0.1)',
                            background: isSelected 
                              ? `${category.color}25` 
                              : 'rgba(255, 255, 255, 0.05)',
                            color: isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.8)',
                            boxShadow: isSelected 
                              ? `0 0 12px ${category.color}40` 
                              : 'none',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                            fontSize: '13px',
                            fontWeight: isSelected ? 600 : 400,
                            userSelect: 'none'
                          }}
                          onMouseEnter={(e) => {
                            if (!isSelected) {
                              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!isSelected) {
                              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                            }
                          }}
                        >
                          <span style={{ fontSize: '14px' }}>{category.icon}</span>
                          <span>{category.name}</span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </Space>
      </div>

      {/* 操作按钮 - 只有解析成功后才显示 */}
      {videoInfo && (
        <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'center', gap: '12px' }}>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={handleDownload}
            loading={downloading}
            disabled={!url.trim()}
            size="large"
            style={{
              background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
              border: 'none',
              borderRadius: '12px',
              height: '48px',
              padding: '0 32px',
              fontSize: '16px',
              fontWeight: 600,
              boxShadow: '0 4px 20px rgba(79, 172, 254, 0.3)',
              minWidth: '160px'
            }}
          >
            {downloading ? 'Importando...' : 'Iniciar importacion'}
          </Button>
          
          {downloading && (
            <Button
              onClick={stopDownload}
              size="large"
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                border: '1px solid rgba(255, 255, 255, 0.3)',
                color: '#ffffff',
                borderRadius: '12px',
                height: '48px',
                padding: '0 24px',
                fontSize: '14px'
              }}
            >
              Detener monitoreo
            </Button>
          )}
        </div>
      )}

      {/* 下载进度 */}
      {currentTask && (
        <Card
          style={{
            background: 'rgba(38, 38, 38, 0.8)',
            border: '1px solid rgba(79, 172, 254, 0.3)',
            borderRadius: '12px',
            marginTop: '16px',
            backdropFilter: 'blur(10px)'
          }}
          styles={{
            body: { padding: '16px' }
          }}
        >
          <div style={{ marginBottom: '16px' }}>
            <Text style={{ color: '#ffffff', fontWeight: 600, fontSize: '18px' }}>Progreso de importacion</Text>
          </div>
          
          {currentTask.video_info && (
            <div style={{ marginBottom: '16px' }}>
              <Text style={{ color: '#4facfe', fontWeight: 600, fontSize: '16px' }}>{currentTask.video_info.title}</Text>
            </div>
          )}
          
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <Text style={{ color: '#cccccc', fontSize: '14px' }}>Estado: {currentTask.status}</Text>
              <Text style={{ color: '#cccccc', fontSize: '14px' }}>{Math.round(currentTask.progress)}%</Text>
            </div>
            
            <Progress
              percent={Math.round(currentTask.progress)}
              status={currentTask.status === 'failed' ? 'exception' : 'active'}
              strokeColor={{
                '0%': '#4facfe',
                '100%': '#00f2fe'
              }}
              trailColor="rgba(255, 255, 255, 0.1)"
              strokeWidth={8}
              showInfo={false}
            />
          </div>
          
          {currentTask.error_message && (
            <div style={{ 
              marginTop: '16px',
              padding: '12px',
              background: 'rgba(255, 77, 79, 0.1)',
              border: '1px solid rgba(255, 77, 79, 0.3)',
              borderRadius: '8px'
            }}>
              <Text style={{ color: '#ff4d4f', fontSize: '14px' }}>Error: {currentTask.error_message}</Text>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

export default BilibiliDownload
