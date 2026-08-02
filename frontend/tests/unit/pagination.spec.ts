import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PaginationControls from '~/components/PaginationControls.vue'

describe('PaginationControls', () => {
  it('renders nothing when there are no results', () => {
    const wrapper = mount(PaginationControls, {
      props: { page: 1, pageSize: 25, total: 0 },
    })
    expect(wrapper.find('nav').exists()).toBe(false)
  })

  it('disables previous on the first page and next on the last', () => {
    const first = mount(PaginationControls, { props: { page: 1, pageSize: 25, total: 50 } })
    expect(first.get('[aria-label="Previous page"]').attributes('disabled')).toBeDefined()
    expect(first.get('[aria-label="Next page"]').attributes('disabled')).toBeUndefined()

    const last = mount(PaginationControls, { props: { page: 2, pageSize: 25, total: 50 } })
    expect(last.get('[aria-label="Next page"]').attributes('disabled')).toBeDefined()
  })

  it('emits the requested page on navigation', async () => {
    const wrapper = mount(PaginationControls, {
      props: { page: 1, pageSize: 25, total: 100 },
    })
    await wrapper.get('[aria-label="Next page"]').trigger('click')
    expect(wrapper.emitted('change')).toEqual([[2]])

    await wrapper.get('[aria-label="Page 3"]').trigger('click')
    expect(wrapper.emitted('change')).toEqual([[2], [3]])
  })

  it('marks the current page with aria-current', () => {
    const wrapper = mount(PaginationControls, {
      props: { page: 2, pageSize: 25, total: 100 },
    })
    expect(wrapper.get('[aria-label="Page 2"]').attributes('aria-current')).toBe('page')
  })
})
