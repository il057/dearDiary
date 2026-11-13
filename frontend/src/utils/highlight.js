const escapeRegExp = (str) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/**
 * 将文本按搜索关键词/关联实体拆分为高亮片段，避免使用 v-html 带来的 XSS 风险
 * @param {string} text
 * @param {string[]} terms
 * @returns {{ text: string, match: boolean }[]}
 */
export const splitHighlightSegments = (text, terms = []) => {
  if (!text) return []
  const cleaned = Array.from(
    new Set(
      (terms || [])
        .map(t => (t || '').trim())
        .filter(Boolean)
    )
  ).sort((a, b) => b.length - a.length)

  if (cleaned.length === 0) {
    return [{ text, match: false }]
  }

  const pattern = cleaned.map(escapeRegExp).join('|')
  const regex = new RegExp(`(${pattern})`, 'gi')
  const parts = text.split(regex)

  return parts
    .map((part, idx) => ({
      text: part,
      match: idx % 2 === 1
    }))
    .filter(seg => seg.text.length > 0)
}

/**
 * 判断实体标签是否命中当前搜索词或关联实体
 * @param {string} entity
 * @param {string[]} terms
 * @returns {boolean}
 */
export const isEntityHighlighted = (entity, terms = []) => {
  if (!entity || !terms || terms.length === 0) return false
  const lowerEnt = entity.toLowerCase()
  return terms.some(t => {
    const clean = (t || '').trim().toLowerCase()
    if (!clean) return false
    return lowerEnt === clean || lowerEnt.includes(clean)
  })
}

