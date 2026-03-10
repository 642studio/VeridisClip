const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1'

const normalizeUrl = (value: string): string => value.replace(/\/+$/, '')

const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL
const API_BASE_URL = normalizeUrl(rawApiBaseUrl)
const API_ORIGIN = API_BASE_URL.replace(/\/api\/v1\/?$/, '')

export const getApiBaseUrl = (): string => API_BASE_URL

export const getApiOrigin = (): string => API_ORIGIN

export const buildApiUrl = (path: string): string => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}

export const getWsBaseUrl = (): string => {
  const explicitWsUrl = import.meta.env.VITE_WS_BASE_URL?.trim()
  if (explicitWsUrl) {
    return normalizeUrl(explicitWsUrl)
  }
  if (API_ORIGIN.startsWith('https://')) {
    return API_ORIGIN.replace('https://', 'wss://')
  }
  if (API_ORIGIN.startsWith('http://')) {
    return API_ORIGIN.replace('http://', 'ws://')
  }
  return `ws://${API_ORIGIN}`
}

export const buildWsUrl = (path: string): string => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${getWsBaseUrl()}${normalizedPath}`
}
