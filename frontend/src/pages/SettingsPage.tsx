import React, { useState, useEffect } from 'react'
import { Layout, Card, Form, Input, Button, Typography, Space, Alert, Divider, Row, Col, Tabs, message, Select, Tag, Switch } from 'antd'
import { KeyOutlined, SaveOutlined, ApiOutlined, SettingOutlined, InfoCircleOutlined, UserOutlined, RobotOutlined } from '@ant-design/icons'
import { settingsApi, getApiBaseUrl } from '../services/api'
import BilibiliManager from '../components/BilibiliManager'
import './SettingsPage.css'

const { Content } = Layout
const { Title, Text, Paragraph } = Typography
const { TabPane } = Tabs

const SettingsPage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [showBilibiliManager, setShowBilibiliManager] = useState(false)
  const [availableModels, setAvailableModels] = useState<any>({})
  const [currentProvider, setCurrentProvider] = useState<any>({})
  const [selectedProvider, setSelectedProvider] = useState('dashscope')

  // 提供商配置
  const providerConfig = {
    dashscope: {
      name: 'Qwen (Alibaba)',
      icon: <RobotOutlined />,
      color: '#1890ff',
      description: 'Servicio Qwen de Alibaba Cloud',
      apiKeyField: 'dashscope_api_key',
      placeholder: 'Ingresa la API key de Qwen'
    },
    openai: {
      name: 'OpenAI',
      icon: <RobotOutlined />,
      color: '#52c41a',
      description: 'Modelos GPT de OpenAI',
      apiKeyField: 'openai_api_key',
      placeholder: 'Ingresa la API key de OpenAI'
    },
    gemini: {
      name: 'Google Gemini',
      icon: <RobotOutlined />,
      color: '#faad14',
      description: 'Modelos Google Gemini',
      apiKeyField: 'gemini_api_key',
      placeholder: 'Ingresa la API key de Gemini'
    },
    siliconflow: {
      name: 'SiliconFlow',
      icon: <RobotOutlined />,
      color: '#722ed1',
      description: 'Servicio de modelos SiliconFlow',
      apiKeyField: 'siliconflow_api_key',
      placeholder: 'Ingresa la API key de SiliconFlow'
    }
  }

  // 加载数据
  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [settings, models, provider] = await Promise.all([
        settingsApi.getSettings(),
        settingsApi.getAvailableModels(),
        settingsApi.getCurrentProvider()
      ])
      
      setAvailableModels(models)
      setCurrentProvider(provider)
      setSelectedProvider(settings.llm_provider || 'dashscope')
      
      // 设置表单初始值
      form.setFieldsValue(settings)
    } catch (error) {
      console.error('Error al cargar datos:', error)
    }
  }

  const getPreferredModelForProvider = (provider: string): string => {
    const providerModels = availableModels?.[provider] || []
    if (!providerModels.length) return ''
    return providerModels[0].name
  }

  // Guardar configuracion
  const handleSave = async (values: any) => {
    try {
      setLoading(true)
      await settingsApi.updateSettings({
        ...values,
        llm_provider: selectedProvider
      })
      message.success('Configuracion guardada correctamente')
      await loadData()
    } catch (error: any) {
      message.error('Error al guardar: ' + (error?.userMessage || error?.message || 'error desconocido'))
    } finally {
      setLoading(false)
    }
  }

  // 测试API密钥
  const handleTestApiKey = async () => {
    const apiKey = form.getFieldValue(providerConfig[selectedProvider as keyof typeof providerConfig].apiKeyField)
    const modelName = form.getFieldValue('model_name')
    
    if (!apiKey) {
      message.error('Primero ingresa la API key')
      return
    }

    if (!modelName) {
      message.error('Primero selecciona un modelo')
      return
    }

    try {
      setLoading(true)
      await settingsApi.updateSettings({
        ...form.getFieldsValue(),
        llm_provider: selectedProvider,
        model_name: modelName
      })
      const result = await settingsApi.testApiKey(selectedProvider, apiKey, modelName)
      if (result.success) {
        message.success('API key validada correctamente')
      } else {
        message.error('Error al validar API key: ' + (result.error || 'error desconocido'))
      }
    } catch (error: any) {
      const friendly =
        error?.userMessage ||
        error?.response?.data?.detail ||
        error?.message ||
        'error desconocido'
      message.error('Prueba fallida: ' + friendly)
      if (!error?.response) {
        message.info(`Backend objetivo: ${getApiBaseUrl()}`, 5)
      }
    } finally {
      setLoading(false)
    }
  }

  // 提供商切换
  const handleProviderChange = (provider: string) => {
    const currentModel = form.getFieldValue('model_name')
    const providerModels = availableModels?.[provider] || []
    const modelIsValidForProvider = providerModels.some((m: any) => m.name === currentModel)
    const nextModel = modelIsValidForProvider ? currentModel : getPreferredModelForProvider(provider)
    setSelectedProvider(provider)
    form.setFieldsValue({ llm_provider: provider, model_name: nextModel })
  }

  return (
    <Content className="settings-page">
      <div className="settings-container">
        <Title level={2} className="settings-title">
          <SettingOutlined /> Configuracion del sistema
        </Title>
        
        <Tabs defaultActiveKey="api" className="settings-tabs">
          <TabPane tab="Configuracion de modelo IA" key="api">
            <Card title="Configuracion de modelo IA" className="settings-card">
              <Alert
                message="Soporte para multiples proveedores de modelos"
                description="El sistema admite varios proveedores de IA. Puedes elegir el que mejor se adapte a tu flujo."
                type="info"
                showIcon
                className="settings-alert"
              />
              
              <Form
                form={form}
                layout="vertical"
                className="settings-form"
                onFinish={handleSave}
                initialValues={{
                  llm_provider: 'dashscope',
                  model_name: 'qwen-plus',
                  chunk_size: 5000,
                  min_score_threshold: 0.7,
                  max_clips_per_collection: 5,
                  llm_debug: false
                }}
              >
                {/* 当前提供商状态 */}
                {currentProvider.available && (
                  <Alert
                    message={`Proveedor activo: ${currentProvider.display_name} - ${currentProvider.model}`}
                    type="success"
                    showIcon
                    style={{ marginBottom: 24 }}
                  />
                )}

                {/* 提供商选择 */}
                <Form.Item
                  label="Proveedor de IA"
                  name="llm_provider"
                  className="form-item"
                  rules={[{ required: true, message: 'Selecciona un proveedor de IA' }]}
                >
                  <Select
                    value={selectedProvider}
                    onChange={handleProviderChange}
                    className="settings-input"
                    placeholder="Selecciona un proveedor de IA"
                  >
                    {Object.entries(providerConfig).map(([key, config]) => (
                      <Select.Option key={key} value={key}>
                        <Space>
                          <span style={{ color: config.color }}>{config.icon}</span>
                          <span>{config.name}</span>
                          <Tag color={config.color}>{config.description}</Tag>
                        </Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>

                {/* 动态API密钥输入 */}
                <Form.Item
                  label={`${providerConfig[selectedProvider as keyof typeof providerConfig].name} API Key`}
                  name={providerConfig[selectedProvider as keyof typeof providerConfig].apiKeyField}
                  className="form-item"
                  rules={[
                    { required: true, message: 'Ingresa la API key' },
                    { min: 10, message: 'La API key debe tener al menos 10 caracteres' }
                  ]}
                >
                  <Input.Password
                    placeholder={providerConfig[selectedProvider as keyof typeof providerConfig].placeholder}
                    prefix={<KeyOutlined />}
                    className="settings-input"
                  />
                </Form.Item>

                {/* 模型选择 */}
                <Form.Item
                  label="Modelo"
                  name="model_name"
                  className="form-item"
                  rules={[{ required: true, message: 'Selecciona un modelo' }]}
                >
                  <Select
                    className="settings-input"
                    placeholder="Selecciona un modelo"
                    showSearch
                    filterOption={(input, option) =>
                      String(option?.value || '').toLowerCase().includes(input.toLowerCase())
                    }
                  >
                    {availableModels[selectedProvider]?.map((model: any) => (
                      <Select.Option key={model.name} value={model.name}>
                        <Space>
                          <span>{model.display_name}</span>
                          <Tag>Max{model.max_tokens} tokens</Tag>
                        </Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item className="form-item">
                  <Space>
                    <Button
                      type="default"
                      icon={<ApiOutlined />}
                      className="test-button"
                      onClick={handleTestApiKey}
                      loading={loading}
                    >
                      Probar conexion
                    </Button>
                  </Space>
                </Form.Item>

                <Form.Item
                  label="Modo debug LLM"
                  name="llm_debug"
                  valuePropName="checked"
                  className="form-item"
                >
                  <Switch checkedChildren="ON" unCheckedChildren="OFF" />
                </Form.Item>

                <Divider className="settings-divider" />

                <Title level={4} className="section-title">Configuracion del modelo</Title>
                
                <Row gutter={16}>
                  <Col span={24}>
                    <Form.Item
                      label="Tamano de bloque de texto"
                      name="chunk_size"
                      className="form-item"
                    >
                      <Input 
                        type="number" 
                        placeholder="5000" 
                        addonAfter="caracteres" 
                        className="settings-input"
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Umbral minimo de puntuacion"
                      name="min_score_threshold"
                      className="form-item"
                    >
                      <Input 
                        type="number" 
                        step="0.1" 
                        min="0" 
                        max="1" 
                        placeholder="0.7" 
                        className="settings-input"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Maximo de clips por coleccion"
                      name="max_clips_per_collection"
                      className="form-item"
                    >
                      <Input 
                        type="number" 
                        placeholder="5" 
                        addonAfter="clips" 
                        className="settings-input"
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item className="form-item">
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<SaveOutlined />}
                    size="large"
                    className="save-button"
                    loading={loading}
                  >
                    Guardar configuracion
                  </Button>
                </Form.Item>
              </Form>
            </Card>

            <Card title="Guia de uso" className="settings-card">
              <Space direction="vertical" size="large" className="instructions-space">
                <div className="instruction-item">
                  <Title level={5} className="instruction-title">
                    <InfoCircleOutlined /> 1. Proveedor de IA
                  </Title>
                  <Paragraph className="instruction-text">
                    El sistema soporta multiples proveedores de IA:
                    <br />• <Text strong>Qwen (Alibaba)</Text>: obtener API key en Alibaba Cloud.
                    <br />• <Text strong>OpenAI</Text>: obtener API key en platform.openai.com.
                    <br />• <Text strong>Google Gemini</Text>: obtener API key en ai.google.dev.
                    <br />• <Text strong>SiliconFlow</Text>: obtener API key en docs.siliconflow.cn.
                  </Paragraph>
                </div>
                
                <div className="instruction-item">
                  <Title level={5} className="instruction-title">
                    <InfoCircleOutlined /> 2. Parametros recomendados
                  </Title>
                  <Paragraph className="instruction-text">
                    • <Text strong>Tamano de bloque de texto</Text>: afecta velocidad y precision. Recomendado: 5000 caracteres.<br />
                    • <Text strong>Umbral de puntuacion</Text>: solo se conservan clips por encima de este valor.<br />
                    • <Text strong>Cantidad de clips por coleccion</Text>: define cuantos clips incluye cada coleccion tematica.
                  </Paragraph>
                </div>
                
                <div className="instruction-item">
                  <Title level={5} className="instruction-title">
                    <InfoCircleOutlined /> 3. Probar conexion
                  </Title>
                  <Paragraph className="instruction-text">
                    Antes de guardar, prueba la API key para confirmar que el servicio responde correctamente.
                  </Paragraph>
                </div>
              </Space>
            </Card>
          </TabPane>

          <TabPane tab="Gestion de Bilibili" key="bilibili">
            <Card title="Cuentas de Bilibili" className="settings-card">
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <div style={{ marginBottom: '24px' }}>
                  <UserOutlined style={{ fontSize: '48px', color: '#1890ff', marginBottom: '16px' }} />
                  <Title level={3} style={{ color: '#ffffff', margin: '0 0 8px 0' }}>
                    Cuentas de Bilibili
                  </Title>
                  <Text type="secondary" style={{ color: '#b0b0b0', fontSize: '16px' }}>
                    Administra tus cuentas de Bilibili con soporte multi-cuenta y publicacion rapida.
                  </Text>
                </div>
                
                <Space size="large">
                  <Button
                    type="primary"
                    size="large"
                    icon={<UserOutlined />}
                    onClick={() => message.info('En desarrollo', 3)}
                    style={{
                      borderRadius: '8px',
                      background: 'linear-gradient(45deg, #1890ff, #36cfc9)',
                      border: 'none',
                      fontWeight: 500,
                      height: '48px',
                      padding: '0 32px',
                      fontSize: '16px'
                    }}
                  >
                    Gestionar cuentas Bilibili
                  </Button>
                </Space>
                
                <div style={{ marginTop: '32px', textAlign: 'left', maxWidth: '600px', margin: '32px auto 0' }}>
                  <Title level={4} style={{ color: '#ffffff', marginBottom: '16px' }}>
                    Funcionalidades
                  </Title>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
                    <div style={{ 
                      padding: '16px', 
                      background: 'rgba(255,255,255,0.05)', 
                      borderRadius: '8px',
                      border: '1px solid #404040'
                    }}>
                      <Text strong style={{ color: '#1890ff' }}>Soporte multi-cuenta</Text>
                      <br />
                      <Text type="secondary" style={{ color: '#b0b0b0' }}>
                        Soporta multiples cuentas de Bilibili para gestion y cambio rapido.
                      </Text>
                    </div>
                    <div style={{ 
                      padding: '16px', 
                      background: 'rgba(255,255,255,0.05)', 
                      borderRadius: '8px',
                      border: '1px solid #404040'
                    }}>
                      <Text strong style={{ color: '#52c41a' }}>Inicio de sesion seguro</Text>
                      <br />
                      <Text type="secondary" style={{ color: '#b0b0b0' }}>
                        Importacion por cookie para una autenticacion mas estable.
                      </Text>
                    </div>
                    <div style={{ 
                      padding: '16px', 
                      background: 'rgba(255,255,255,0.05)', 
                      borderRadius: '8px',
                      border: '1px solid #404040'
                    }}>
                      <Text strong style={{ color: '#faad14' }}>Publicacion rapida</Text>
                      <br />
                      <Text type="secondary" style={{ color: '#b0b0b0' }}>
                        Publica desde el detalle del clip seleccionando cuenta.
                      </Text>
                    </div>
                    <div style={{ 
                      padding: '16px', 
                      background: 'rgba(255,255,255,0.05)', 
                      borderRadius: '8px',
                      border: '1px solid #404040'
                    }}>
                      <Text strong style={{ color: '#722ed1' }}>Gestion masiva</Text>
                      <br />
                      <Text type="secondary" style={{ color: '#b0b0b0' }}>
                        Soporta carga por lotes de clips para mayor eficiencia.
                      </Text>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </TabPane>
        </Tabs>

        {/* Gestion de Bilibili弹窗 */}
        <BilibiliManager
          visible={showBilibiliManager}
          onClose={() => setShowBilibiliManager(false)}
          onUploadSuccess={() => {
            message.success('Operacion exitosa')
          }}
        />
      </div>
    </Content>
  )
}

export default SettingsPage
