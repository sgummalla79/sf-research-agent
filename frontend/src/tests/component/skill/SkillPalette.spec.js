/**
 * Component tests for SkillPalette.vue
 *
 * Tests: filter by query, keyboard navigation (ArrowDown/Up/Enter/Escape),
 *        click to select, empty state.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import SkillPalette from '../../../components/skill/SkillPalette.vue'

const SKILLS = [
  { id: 's1', name: 'Architect', description: 'System design', icon: '🏗️' },
  { id: 's2', name: 'Researcher', description: 'Web search',   icon: '🔍' },
  { id: 's3', name: 'Reviewer',  description: 'Code review',   icon: '✅' },
]

function factory(props = {}) {
  return mount(SkillPalette, {
    props: { skills: SKILLS, query: '', ...props },
    attachTo: document.body,
  })
}

beforeEach(() => { document.body.innerHTML = '' })

describe('rendering', () => {
  it('renders all skills when query is empty', () => {
    const w = factory()
    expect(w.findAll('.palette-row')).toHaveLength(3)
  })

  it('shows skill name and description', () => {
    const w = factory()
    const rows = w.findAll('.palette-row')
    expect(rows[0].text()).toContain('Architect')
    expect(rows[0].text()).toContain('System design')
  })

  it('shows empty state when no skills match query', () => {
    const w = factory({ query: 'zzznomatch' })
    expect(w.find('.palette-empty').exists()).toBe(true)
    expect(w.findAll('.palette-row')).toHaveLength(0)
  })
})

describe('filtering by query', () => {
  it('filters by skill name (case-insensitive)', () => {
    // 'archi' is specific enough — 'researcher'.includes('archi') is false
    const w = factory({ query: 'archi' })
    const rows = w.findAll('.palette-row')
    expect(rows).toHaveLength(1)
    expect(rows[0].text()).toContain('Architect')
  })

  it('filters by description', () => {
    const w = factory({ query: 'web' })
    const rows = w.findAll('.palette-row')
    expect(rows).toHaveLength(1)
    expect(rows[0].text()).toContain('Researcher')
  })

  it('shows all when query matches multiple', () => {
    const w = factory({ query: 'r' })
    // Researcher and Reviewer both have 'r'
    expect(w.findAll('.palette-row').length).toBeGreaterThanOrEqual(2)
  })
})

describe('keyboard navigation', () => {
  it('ArrowDown moves active index down', async () => {
    const w = factory()
    await w.trigger('keydown', { key: 'ArrowDown' })
    const rows = w.findAll('.palette-row')
    expect(rows[1].classes()).toContain('active')
  })

  it('ArrowUp moves active index up (clamped at 0)', async () => {
    const w = factory()
    await w.trigger('keydown', { key: 'ArrowDown' })
    await w.trigger('keydown', { key: 'ArrowUp' })
    const rows = w.findAll('.palette-row')
    expect(rows[0].classes()).toContain('active')
  })

  it('Enter emits select with active skill id', async () => {
    const w = factory()
    await w.trigger('keydown', { key: 'ArrowDown' })   // index 1 → Researcher
    await w.trigger('keydown', { key: 'Enter' })
    expect(w.emitted('select')).toBeTruthy()
    expect(w.emitted('select')[0][0]).toBe('s2')
  })

  it('Escape emits dismiss', async () => {
    const w = factory()
    await w.trigger('keydown', { key: 'Escape' })
    expect(w.emitted('dismiss')).toBeTruthy()
  })

  it('Enter on first row emits select with first skill id', async () => {
    const w = factory()
    await w.trigger('keydown', { key: 'Enter' })
    expect(w.emitted('select')[0][0]).toBe('s1')
  })
})

describe('mouse interaction', () => {
  it('clicking a row emits select with that skill id', async () => {
    const w = factory()
    await w.findAll('.palette-row')[2].trigger('click')
    expect(w.emitted('select')[0][0]).toBe('s3')
  })

  it('mouseenter sets active index for keyboard preview', async () => {
    const w = factory()
    await w.findAll('.palette-row')[2].trigger('mouseenter')
    expect(w.findAll('.palette-row')[2].classes()).toContain('active')
  })
})
