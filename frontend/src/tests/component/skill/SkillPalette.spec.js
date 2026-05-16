/**
 * Component tests for SkillPalette.vue
 *
 * Note: keyboard navigation is delegated to the parent via defineExpose
 * (navigateUp, navigateDown, selectActive). The palette itself handles
 * click + mouseenter. Tests use exposed methods directly.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import SkillPalette from '../../../components/skill/SkillPalette.vue'

const SKILLS = [
  { id: 's1', name: 'Architect',  description: 'System design', icon: '🏗️' },
  { id: 's2', name: 'Researcher', description: 'Web search',    icon: '🔍' },
  { id: 's3', name: 'Reviewer',   description: 'Code review',   icon: '✅' },
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

  it('shows skill name in each row', () => {
    const w = factory()
    const rows = w.findAll('.palette-row')
    expect(rows[0].text()).toContain('Architect')
    expect(rows[1].text()).toContain('Researcher')
  })

  it('shows skill icon in each row', () => {
    const w = factory()
    expect(w.findAll('.palette-row')[0].text()).toContain('🏗️')
  })

  it('shows empty state when no skills match query', () => {
    const w = factory({ query: 'zzznomatch' })
    expect(w.find('.palette-empty').exists()).toBe(true)
    expect(w.findAll('.palette-row')).toHaveLength(0)
  })

  it('shows description panel on hover', async () => {
    const w = factory()
    await w.findAll('.palette-row')[0].trigger('mouseenter')
    expect(w.find('.palette-desc').exists()).toBe(true)
    expect(w.find('.palette-desc').text()).toContain('System design')
  })

  it('hides description panel when not hovering', () => {
    const w = factory()
    expect(w.find('.palette-desc').exists()).toBe(false)
  })
})

describe('filtering by query', () => {
  it('filters by skill name (case-insensitive)', () => {
    const w = factory({ query: 'archi' })
    expect(w.findAll('.palette-row')).toHaveLength(1)
    expect(w.findAll('.palette-row')[0].text()).toContain('Architect')
  })

  it('filters by skill id', () => {
    const w = factory({ query: 's2' })
    expect(w.findAll('.palette-row')).toHaveLength(1)
    expect(w.findAll('.palette-row')[0].text()).toContain('Researcher')
  })

  it('shows all when query matches multiple', () => {
    const w = factory({ query: 'r' })
    expect(w.findAll('.palette-row').length).toBeGreaterThanOrEqual(2)
  })

  it('exposes filtered list matching the rendered rows', () => {
    const w = factory({ query: 'archi' })
    expect(w.vm.filtered).toHaveLength(1)
    expect(w.vm.filtered[0].id).toBe('s1')
  })
})

describe('keyboard navigation via exposed methods', () => {
  it('navigateDown moves active index to next row', async () => {
    const w = factory()
    w.vm.navigateDown()
    await w.vm.$nextTick()
    expect(w.findAll('.palette-row')[1].classes()).toContain('active')
  })

  it('navigateDown is clamped at last item', async () => {
    const w = factory()
    w.vm.navigateDown()
    w.vm.navigateDown()
    w.vm.navigateDown()   // beyond last
    await w.vm.$nextTick()
    const rows = w.findAll('.palette-row')
    expect(rows[rows.length - 1].classes()).toContain('active')
  })

  it('navigateUp is clamped at 0', async () => {
    const w = factory()
    w.vm.navigateUp()     // already at 0
    await w.vm.$nextTick()
    expect(w.findAll('.palette-row')[0].classes()).toContain('active')
  })

  it('selectActive emits select with current active skill id', async () => {
    const w = factory()
    w.vm.navigateDown()   // move to s2
    w.vm.selectActive()
    await w.vm.$nextTick()
    expect(w.emitted('select')?.[0]?.[0]).toBe('s2')
  })

  it('selectActive on first item emits s1', async () => {
    const w = factory()
    w.vm.selectActive()
    await w.vm.$nextTick()
    expect(w.emitted('select')?.[0]?.[0]).toBe('s1')
  })
})

describe('mouse interaction', () => {
  it('clicking a row emits select with that skill id', async () => {
    const w = factory()
    await w.findAll('.palette-row')[2].trigger('click')
    expect(w.emitted('select')?.[0]?.[0]).toBe('s3')
  })

  it('mouseenter sets the active row for visual feedback', async () => {
    const w = factory()
    await w.findAll('.palette-row')[2].trigger('mouseenter')
    expect(w.findAll('.palette-row')[2].classes()).toContain('active')
  })
})
