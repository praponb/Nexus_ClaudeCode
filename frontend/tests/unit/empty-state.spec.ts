import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EmptyState from '~/components/EmptyState.vue'

const NuxtLinkStub = {
  props: ['to'],
  template: '<a :href="to"><slot /></a>',
}

describe('EmptyState', () => {
  it('explains what is empty and offers the next action', () => {
    const wrapper = mount(EmptyState, {
      props: {
        title: 'No assets registered yet',
        message: 'Register your first asset.',
        actionTo: '/assets/new',
        actionLabel: 'Register asset',
      },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(wrapper.find('h2').text()).toBe('No assets registered yet')
    expect(wrapper.text()).toContain('Register your first asset.')
    const link = wrapper.find('a')
    expect(link.attributes('href')).toBe('/assets/new')
    expect(link.text()).toContain('Register asset')
  })

  it('renders slot content for custom actions', () => {
    const wrapper = mount(EmptyState, {
      props: { title: 'No results' },
      slots: { default: '<button>Clear filters</button>' },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(wrapper.find('button').text()).toBe('Clear filters')
  })
})
