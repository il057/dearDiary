import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export const diaryApi = {
  getDiaries(skip = 0, limit = 500) {
    return api.get('/diaries', { params: { skip, limit } })
  },

  getSingleDiary(id) {
    return api.get(`/diaries/${id}`)
  },
  
  createDiary(content, created_at = null) {
    const payload = { content }
    if (created_at) {
      payload.created_at = created_at
    }
    return api.post('/diaries', payload)
  },

  updateDiary(id, content, created_at = null) {
    const payload = { content }
    if (created_at) {
      payload.created_at = created_at
    }
    return api.put(`/diaries/${id}`, payload)
  },

  reindexSingle(id) {
    return api.post(`/diaries/${id}/reindex`)
  },
  
  search(q) {
    return api.get('/search', { params: { q } })
  },

  // 获取 2D 力导向聚类星系图数据
  getClusterGraph2D() {
    return api.get('/graph/cluster2d')
  },

  // 手工增删改单篇日记的标签
  updateDiaryEntities(id, entities) {
    return api.put(`/diaries/${id}/entities`, { entities })
  },

  // 手工修改单篇日记的心情词
  updateDiaryMood(id, mood) {
    return api.put(`/diaries/${id}/mood`, { mood })
  },

  // 获取认知词典与别名列表
  getKnowledge() {
    return api.get('/knowledge')
  },

  // 绑定别名
  setAlias(alias, canonical) {
    return api.post('/knowledge/alias', { alias, canonical })
  },

  // 删除别名
  deleteAlias(alias) {
    return api.delete(`/knowledge/alias/${encodeURIComponent(alias)}`)
  },

  // 删除实体
  deleteEntity(name) {
    return api.delete(`/knowledge/entity/${encodeURIComponent(name)}`)
  },

  // 修改实体的类型分类 (person/pet/place/time/concept)
  updateEntityType(name, entity_type) {
    return api.put('/knowledge/entity', { name, entity_type })
  },

  deleteDiary(id) {
    return api.delete(`/diaries/${id}`)
  },

  exportDiaries() {
    return api.get('/export')
  },

  importDiaries(diaries) {
    return api.post('/import', { diaries })
  }
}
