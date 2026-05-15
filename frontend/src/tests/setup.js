// Global test setup — runs before every test file
import { vi } from 'vitest'

// Silence Vue Router warnings in component tests
vi.mock('vue-router', () => ({
  useRouter:  () => ({ push: vi.fn() }),
  useRoute:   () => ({ params: {}, query: {} }),
  RouterView: { template: '<div />' },
}))

// Prevent window.matchMedia errors in happy-dom
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media:   query,
    onchange: null,
    addEventListener:    vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent:       vi.fn(),
  })),
})
