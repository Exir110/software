import { reactive } from 'vue'
import { request, setToken, clearToken, getToken } from '../api/client'
import type { TokenResponse, User } from '../api/types'

export const session = reactive({
  user: null as User | null,
  checking: true,
})

export async function restoreSession(): Promise<void> {
  if (!getToken()) {
    session.checking = false
    return
  }
  try {
    session.user = await request<User>('/auth/me')
  } catch {
    clearToken()
    session.user = null
  } finally {
    session.checking = false
  }
}

export async function login(username: string, password: string): Promise<void> {
  const response = await request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: { username, password },
  })
  setToken(response.access_token)
  session.user = response.user
}

export async function register(
  username: string,
  password: string,
  displayName: string,
): Promise<void> {
  const response = await request<TokenResponse>('/auth/register', {
    method: 'POST',
    body: { username, password, display_name: displayName },
  })
  setToken(response.access_token)
  session.user = response.user
}

export function logout(): void {
  clearToken()
  session.user = null
}
