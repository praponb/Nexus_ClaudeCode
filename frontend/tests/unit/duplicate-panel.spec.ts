import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AssetDuplicatePanel from '~/components/asset/AssetDuplicatePanel.vue'
import type { DuplicateWarning } from '~/types/api'

/** Shape returned by services.find_duplicate_warnings (BR-008). */
const serialWarning: DuplicateWarning = {
  code: 'POSSIBLE_DUPLICATE_SERIAL',
  message: "1 active asset(s) already use serial number 'SN-1'.",
  matches: [{ uuid: 'uuid-a', tag: 'AST-000001', name: 'Developer laptop' }],
}

const modelWarning: DuplicateWarning = {
  code: 'SIMILAR_MANUFACTURER_MODEL',
  message: "2 active asset(s) share manufacturer 'Dell' and model 'Latitude'.",
  matches: [
    { uuid: 'uuid-b', tag: 'AST-000002', name: 'Spare laptop' },
    { uuid: 'uuid-c', tag: 'AST-000003', name: 'Loaner laptop' },
  ],
}

const stubs = { NuxtLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } }

function render(warnings: DuplicateWarning[]) {
  return mount(AssetDuplicatePanel, { props: { warnings }, global: { stubs } })
}

describe('AssetDuplicatePanel', () => {
  it('renders each warning message as readable text', () => {
    const text = render([serialWarning]).text()
    // Regression: warnings are objects, so join()/interpolating the object
    // rendered the panel as "[object Object]".
    expect(text).not.toContain('[object Object]')
    expect(text).toContain("1 active asset(s) already use serial number 'SN-1'.")
  })

  it('lists the matched assets so they can be reviewed', () => {
    const wrapper = render([serialWarning])
    expect(wrapper.text()).toContain('AST-000001')
    expect(wrapper.text()).toContain('Developer laptop')
    const links = wrapper.findAll('a').map((a) => a.attributes('href'))
    expect(links).toContain('/assets/uuid-a')
  })

  it('keeps each rule grouped with the assets it matched', () => {
    const sections = render([serialWarning, modelWarning]).findAll('section')
    expect(sections).toHaveLength(2)
    expect(sections[0]!.text()).toContain('AST-000001')
    expect(sections[0]!.text()).not.toContain('AST-000002')
    expect(sections[1]!.text()).toContain('AST-000002')
    expect(sections[1]!.text()).toContain('AST-000003')
  })

  it('always explains what the panel is', () => {
    expect(render([serialWarning]).text()).toContain('Possible duplicate assets')
  })

  it('renders without matches or warnings rather than throwing', () => {
    expect(render([{ ...serialWarning, matches: [] }]).text()).toContain(serialWarning.message)
    expect(render([]).text()).toContain('Possible duplicate assets')
  })
})
