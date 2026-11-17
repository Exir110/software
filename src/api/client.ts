const BASE = ((import.meta.env.VITE_API_BASE as string | undefined) ?? '/api').replace(/\/$/, '')
const TOKEN_KEY = 'ytx-token'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
}

function detailOf(data: unknown, status: number): string {
  if (data && typeof data === 'object') {
    const detail = (data as { detail?: unknown }).detail
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === 'object' && 'msg' in item) {
            return String((item as { msg: unknown }).msg)
          }
          return '参数格式不正确'
        })
        .join('；')
    }
    if (typeof detail === 'string') return detail
  }
  return `请求失败（${status}）`
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let body: string | undefined
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body,
      signal: options.signal,
    })
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    throw new ApiError(0, '无法连接后端服务，请确认 API 已在 8000 端口启动')
  }

  if (response.status === 204) return undefined as T

  const text = await response.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearToken()
      window.dispatchEvent(new CustomEvent('ytx-unauthorized'))
    }
    throw new ApiError(response.status, detailOf(data, response.status))
  }
  return data as T
}

