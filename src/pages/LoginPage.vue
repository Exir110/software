<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { login, register } from '../stores/session'
import { notify } from '../stores/toast'

const mode = ref<'login' | 'register'>('login')
const busy = ref(false)
const errorMessage = ref('')
const form = reactive({
  username: 'demo',
  password: 'demo1234',
  display_name: '考研同学',
})

function fillDemo(): void {
  mode.value = 'login'
  form.username = 'demo'
  form.password = 'demo1234'
  errorMessage.value = ''
}

async function submit(): Promise<void> {
  errorMessage.value = ''
  if (form.username.trim().length < 3) {
    errorMessage.value = '用户名至少 3 个字符'
    return
  }
  if (form.password.length < 6) {
    errorMessage.value = '密码至少 6 个字符'
    return
  }
  if (mode.value === 'register' && !form.display_name.trim()) {
    errorMessage.value = '请填写显示名称'
    return
  }
  busy.value = true
  try {
    if (mode.value === 'login') {
      await login(form.username.trim(), form.password)
      notify('欢迎回来')
    } else {
      await register(form.username.trim(), form.password, form.display_name.trim())
      notify('账号已创建，欢迎使用')
    }
  } catch (error) {
    errorMessage.value = (error as Error).message
  } finally {
    busy.value = false
  }
}

const modeTitle = computed(() => (mode.value === 'login' ? '登录你的备考空间' : '创建备考账号'))
</script>

<template>
  <div class="login-shell">
    <div class="login-card">
      <div class="login-brand">
        <div class="brand-mark">研</div>
        <div>
          <strong>研途智学</strong>
          <span>个人备考工作台</span>
        </div>
      </div>
      <p class="overline">Welcome back</p>
      <h1 class="login-title">{{ modeTitle }}</h1>
      <p class="login-subtitle">登录后，任务、学习记录与掌握度会保存到后端数据库，不再只存在浏览器里。</p>

      <form class="login-form" @submit.prevent="submit">
        <label>用户名<input v-model="form.username" autocomplete="username" maxlength="32" placeholder="3-32 位字符"></label>
        <label v-if="mode === 'register'">显示名称<input v-model="form.display_name" maxlength="64" placeholder="例如：林同学"></label>
        <label>密码<input v-model="form.password" type="password" autocomplete="current-password" maxlength="128" placeholder="至少 6 位"></label>
        <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>
        <button class="primary-button full-button" type="submit" :disabled="busy">
          {{ busy ? '请稍候…' : mode === 'login' ? '登录' : '注册并登录' }}
        </button>
      </form>

      <div class="login-switch">
        <template v-if="mode === 'login'">
          还没有账号？
          <button type="button" @click="mode = 'register'; errorMessage = ''">立即注册</button>
        </template>
        <template v-else>
          已有账号？
          <button type="button" @click="mode = 'login'; errorMessage = ''">返回登录</button>
        </template>
      </div>

      <button class="demo-account" type="button" @click="fillDemo">
        演示账号：demo / demo1234
      </button>
    </div>
    <p class="login-footnote">研途智学 · 学习规划与知识追踪</p>
  </div>
</template>
