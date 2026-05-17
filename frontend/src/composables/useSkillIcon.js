import { computed } from 'vue'
import { useDarkMode } from './useDarkMode'

const SKILL_SVG_ICONS = ['architect']

export function useSkillIcon() {
  const { isDark } = useDarkMode()

  function skillIconUrl(skillId) {
    if (!SKILL_SVG_ICONS.includes(skillId)) return null
    return isDark.value ? '/icons/skill-dark.svg' : '/icons/skill-light.svg'
  }

  return { skillIconUrl }
}
