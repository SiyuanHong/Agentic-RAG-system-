const TOKEN_KEY = 'auth_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/**
 * Check if the stored JWT is expired (with a 60s buffer).
 * Returns true if token is valid/present, false if expired or missing.
 */
export function isTokenValid(): boolean {
  const token = getToken()
  if (!token) return false
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    // exp is in seconds, Date.now() in ms — add 60s buffer
    return payload.exp * 1000 > Date.now() + 60_000
  } catch {
    return false
  }
}
