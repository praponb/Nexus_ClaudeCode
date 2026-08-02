import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import InlineAlert from '~/components/InlineAlert.vue'

describe('InlineAlert', () => {
  it('uses role=alert for errors and shows the support reference', () => {
    const wrapper = mount(InlineAlert, {
      props: {
        tone: 'error',
        title: 'Assets could not be loaded',
        message: 'Try again.',
        correlationId: 'abc-123',
      },
    })
    expect(wrapper.attributes('role')).toBe('alert')
    expect(wrapper.text()).toContain('Support reference: abc-123')
  })

  it('emits retry when the retry action is used', async () => {
    const wrapper = mount(InlineAlert, {
      props: { tone: 'error', message: 'Failed', retryLabel: 'Retry' },
    })
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it('uses role=status for informational alerts', () => {
    const wrapper = mount(InlineAlert, {
      props: { tone: 'info', message: 'FYI' },
    })
    expect(wrapper.attributes('role')).toBe('status')
  })
})
