import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AssetStatusBadge from '~/components/asset/AssetStatusBadge.vue'
import StatusBadge from '~/components/StatusBadge.vue'

describe('StatusBadge', () => {
  it('always renders icon + text label (never color alone)', () => {
    const wrapper = mount(StatusBadge, {
      props: { label: 'Available', code: 'available' },
    })
    expect(wrapper.text()).toContain('Available')
    expect(wrapper.find('svg').exists()).toBe(true)
    expect(wrapper.find('svg').attributes('aria-hidden')).toBe('true')
  })

  it('applies the semantic treatment class', () => {
    const wrapper = mount(StatusBadge, {
      props: { label: 'Lost', code: 'lost' },
    })
    expect(wrapper.classes().join(' ')).toContain('text-danger')
  })

  it('prefers the backend treatment hint over the code guess', () => {
    const wrapper = mount(StatusBadge, {
      props: { label: 'In repair', code: 'unknown_code', treatmentHint: 'warning' },
    })
    expect(wrapper.classes().join(' ')).toContain('text-warning')
  })
})

describe('AssetStatusBadge', () => {
  it('renders the status label from the API reference', () => {
    const wrapper = mount(AssetStatusBadge, {
      props: {
        status: { uuid: '1', code: 'assigned', label: 'Assigned', semantic_treatment: 'success' },
      },
    })
    expect(wrapper.text()).toContain('Assigned')
  })

  it('renders an explicit fallback for missing status', () => {
    const wrapper = mount(AssetStatusBadge, { props: { status: null } })
    expect(wrapper.text()).toContain('Unknown status')
  })
})
