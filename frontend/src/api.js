import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 60000,
})

export async function askKnowledge(question, history = [], conversationId = null) {
  const response = await api.post('/api/chat/query', {
    message: question,
    conversation_id: conversationId,
    history: history.map((item) => ({
      role: item.role,
      content: item.content,
    })),
  })
  return response.data
}
