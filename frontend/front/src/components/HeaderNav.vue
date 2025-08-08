<template>
  <nav class="nav">
    <div class="left">
      <strong @click="$router.push('/')" class="logo">Eduprize</strong>
      <button @click="$router.push('/')" class="link">Giriş</button>
      <button v-if="role === 'admin'" class="link" @click="$router.push('/admin-dashboard')">Admin Panel</button>
      <button v-if="role === 'business_user'" class="link" @click="$router.push('/business-dashboard')">İşletme Paneli</button>
      <button class="link" @click="$router.push('/play')">Oyun Oyna</button>
      <button class="link" @click="goBack">Geri</button>
    </div>
    <div class="right">
      <span v-if="username" class="user">👤 {{ username }} ({{ roleLabel }})</span>
      <button v-if="username" class="logout" @click="logout">Çıkış</button>
    </div>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const username = ref('')
const role = ref('') // admin | business_user | player | (boş)

const roleLabel = computed(() => {
  if (role.value === 'admin') return 'Admin'
  if (role.value === 'business_user') return 'İşletme'
  if (role.value === 'player') return 'Oyuncu'
  return 'Misafir'
})

const fetchWhoAmI = async () => {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/whoami/', {
      credentials: 'include',
    })
    if (!res.ok) return
    const data = await res.json()
    username.value = data.username
    role.value = data.role
  } catch {}
}

const logout = async () => {
  try {
    await fetch('http://127.0.0.1:8000/api/logout/', {
      method: 'POST',
      credentials: 'include',
    })
  } catch {}
  // Çıkış sonrası login sayfasına
  window.location.href = '/'
}

const goBack = () => {
  // Eğer önceki sayfa yoksa landing'e dön
  if (window.history.length > 1) {
    window.history.back()
  } else {
    window.location.href = '/'
  }
}

onMounted(fetchWhoAmI)
</script>

<style scoped>
.nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: .5rem 1rem; background: #1f1f1f; color: #fff; position: sticky; top: 0; z-index: 10;
}
.left { display: flex; align-items: center; gap: .5rem; }
.right { display: flex; align-items: center; gap: .5rem; }
.logo { cursor: pointer; margin-right: .5rem; }
.link, .logout {
  background: transparent; border: 1px solid #444; color: #fff; padding: .35rem .6rem;
  border-radius: 8px; cursor: pointer;
}
.link:hover, .logout:hover { background: #2b2b2b; }
.user { opacity: .85; margin-right: .5rem; }
</style>
