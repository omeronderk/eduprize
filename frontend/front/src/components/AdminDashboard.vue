<template>
  <div class="wrap">
    <h1>Admin Paneli</h1>
    <p>Tüm işletmelerin verilerine erişiminiz var.</p>

    <div class="links">
      <router-link to="/gameplays">Tüm Oyun Kayıtlarını Gör</router-link>
      <button @click="logout">Çıkış Yap</button>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { useRouter } from 'vue-router'
const router = useRouter()

const logout = async () => {
  try {
    await axios.post('http://127.0.0.1:8000/api/logout/', {}, { withCredentials: true })
  } catch {}
  router.push('/')
}
</script>

<style scoped>
.wrap { max-width: 900px; margin: 2rem auto; }
.links { display: flex; gap: 1rem; margin-top: 1rem; }
button { padding: .5rem 1rem; }
</style>
