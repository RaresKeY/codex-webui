import { describe, expect, it } from 'vitest'
import { browserAddress } from './browser-address'

describe('browser address normalization', () => {
  it('adds HTTPS to bare and protocol-relative domains without changing paths or queries', () => {
    expect(browserAddress(' duckduckgo.com ')).toBe('https://duckduckgo.com/')
    expect(browserAddress('//example.org/path?q=test#section')).toBe('https://example.org/path?q=test#section')
    expect(browserAddress('example.org:8443/path')).toBe('https://example.org:8443/path')
    expect(browserAddress('example.org/?next=https://other.example/')).toBe('https://example.org/?next=https://other.example/')
  })
  it('preserves explicit web protocols for backend validation', () => {
    expect(browserAddress('https://example.org/path')).toBe('https://example.org/path')
    expect(browserAddress('http://127.0.0.1:18765/fixture')).toBe('http://127.0.0.1:18765/fixture')
  })
  it('rejects empty, malformed, credential-bearing and non-web addresses', () => {
    for (const address of ['', 'some search words', 'https://', 'https://user:password@example.org', 'file:///tmp/example', 'javascript:alert(1)']) expect(browserAddress(address)).toBeNull()
  })
})
