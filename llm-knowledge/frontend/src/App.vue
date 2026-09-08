<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <h1>企业知识库问答</h1>
        <p>基于飞书知识库、Milvus 向量检索与 LangGraph 编排</p>
      </div>
    </header>

    <main class="chat-layout">
      <aside class="sidebar">
        <h3>工作台</h3>
        <ul>
          <li>知识检索</li>
          <li>文档索引</li>
          <li>回答审计</li>
        </ul>
        <div class="status-card">
          <span class="dot"></span>
          已连接知识库
        </div>
      </aside>

      <section class="chat-panel">
        <div class="messages" ref="messagesRef">
          <div v-for="(item, index) in messages" :key="index" :class="['message-row', item.role]">
            <div class="bubble">
              <div class="role">{{ item.role === 'user' ? '用户' : 'AI助手' }}</div>
              <div class="content">{{ item.content }}</div>
            </div>
          </div>
        </div>

        <div class="input-area">
          <el-input
            v-model="input"
            type="textarea"
            :rows="4"
            placeholder="请输入企业问题，例如：请解释员工入职流程"
            resize="none"
            @keyup.enter.exact="handleSubmit"
          />
          <div class="actions">
            <el-tag v-if="loading" type="info">检索中...</el-tag>
            <el-button type="primary" :loading="loading" @click="handleSubmit">提问</el-button>
          </div>
        </div>
      </section>

      <aside class="reference-panel">
        <h3>参考资料</h3>
        <div v-if="sources.length === 0" class="empty-state">暂无参考来源</div>
        <div v-for="(source, index) in sources" :key="index" class="source-card">
          <div class="source-title">{{ source.title }}</div>
          <div class="source-meta">相似度：{{ source.score.toFixed(3) }}</div>
          <p>{{ source.content }}</p>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { ElButton, ElInput, ElTag } from 'element-plus'
import { askKnowledge } from './api'

const messages = ref([
  {
    role: 'assistant',
    content: '您好，我是企业知识库助手。请直接提出你的问题，我会在飞书知识库中进行检索并给出结论。',
  },
])
const input = ref('')
const loading = ref(false)
const sources = ref([])
const conversationId = ref(null)
const messagesRef = ref(null)

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

watch(messages, scrollToBottom, { deep: true })

async function handleSubmit() {
  const question = input.value.trim()
  if (!question || loading.value) return

  messages.value.push({ role: 'user', content: question })
  loading.value = true
  input.value = ''

  try {
    const response = await askKnowledge(question, messages.value.slice(0, -1), conversationId.value)
    conversationId.value = response.conversation_id
    messages.value.push({ role: 'assistant', content: response.answer })
    sources.value = response.sources || []
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，检索过程出现错误，请检查后端服务或配置是否正确。',
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
:global(body) {
  margin: 0;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: linear-gradient(135deg, #f3f7ff, #e9f0ff);
}

* {
  box-sizing: border-box;
}

.app-shell {
  min-height: 100vh;
  padding: 24px;
}

.topbar {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(203, 213, 225, 0.8);
  border-radius: 18px;
  padding: 20px 24px;
  margin-bottom: 20px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.topbar h1 {
  margin: 0;
  font-size: 32px;
}

.topbar p {
  margin: 8px 0 0;
  color: #64748b;
}

.chat-layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 320px;
  gap: 20px;
  min-height: calc(100vh - 170px);
}

.sidebar,
.reference-panel,
.chat-panel {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(203, 213, 225, 0.8);
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.sidebar,
.reference-panel {
  padding: 18px;
}

.sidebar h3,
.reference-panel h3 {
  margin: 0 0 14px;
}

.sidebar ul {
  list-style: none;
  margin: 0 0 20px;
  padding: 0;
  display: grid;
  gap: 10px;
  color: #475569;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #edf7f0;
  color: #166534;
  font-weight: 600;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #22c55e;
  display: inline-block;
}

.chat-panel {
  display: flex;
  flex-direction: column;
  padding: 18px;
}

.messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-right: 8px;
}

.message-row {
  display: flex;
}

.message-row.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 75%;
  padding: 14px 16px;
  border-radius: 16px;
  background: #eff6ff;
  border: 1px solid #dbeafe;
}

.message-row.user .bubble {
  background: #2563eb;
  color: white;
  border-color: #2563eb;
}

.role {
  font-size: 12px;
  opacity: 0.75;
  margin-bottom: 6px;
}

.content {
  white-space: pre-wrap;
  line-height: 1.7;
}

.input-area {
  margin-top: 18px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.empty-state {
  color: #64748b;
  background: #f8fafc;
  padding: 16px;
  border-radius: 12px;
  border: 1px dashed #cbd5e1;
}

.source-card {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 12px;
}

.source-title {
  font-weight: 700;
  margin-bottom: 6px;
}

.source-meta {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
}

@media (max-width: 1100px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }
}
</style>
