import { describe, it, expect, beforeEach } from 'vitest'
import { getToken, setToken, clearToken } from '../auth'

describe('auth token helpers', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('getToken returns stored token', () => {
    localStorage.setItem('auth_token', 'my-jwt')
    expect(getToken()).toBe('my-jwt')
  })

  it('setToken stores token in localStorage', () => {
    setToken('new-token')
    expect(localStorage.getItem('auth_token')).toBe('new-token')
  })

  it('clearToken removes token', () => {
    localStorage.setItem('auth_token', 'to-remove')
    clearToken()
    expect(localStorage.getItem('auth_token')).toBeNull()
  })

  it('getToken returns null when empty', () => {
    expect(getToken()).toBeNull()
  })
})
