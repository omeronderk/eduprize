<template>
  <div class="wrap">
    <h2>Oyun Alanı</h2>
    <button @click="$router.back()" style="margin-bottom:.5rem;">← Geri</button>
    <div class="card">
      <div class="row">
        <label>İşletme Kodu (unique_code)</label>
        <input v-model="businessCode" placeholder="örn. CAFE-NIRVANA" />
      </div>
      <div class="row">
        <button @click="detectBusiness" :disabled="loading">Neredeyim? (IP ile bul)</button>
        <button @click="loadGames" :disabled="loading">Oyunları Getir</button>
        <button @click="loadStatus" :disabled="loading">Kalan Hakkım</button>
      </div>
      <small v-if="businessName">İşletme: <b>{{ businessName }}</b></small>
    </div>

    <div v-if="statusInfo" class="card">
      <h3>Günlük Hak</h3>
      <p>IP: {{ statusInfo.ip }}</p>
      <p>Kullanılan: {{ statusInfo.used }} / {{ statusInfo.limit }} — Kalan: <b>{{ statusInfo.remaining }}</b></p>
    </div>

    <div v-if="games.length" class="card">
      <h3>Oyunlar</h3>
      <ul>
        <li v-for="g in games" :key="g.game_id" class="row">
          <span>{{ g.game_name }}</span>
          <small>kazanma: {{ (g.win_probability * 100).toFixed(0) }}%</small>
          <button @click="play(g.game_id)" :disabled="loading">Oyna</button>
        </li>
      </ul>
    </div>

    <div v-if="result" class="card">
      <h3>Sonuç</h3>
      <p><b>{{ result.game }}</b> — {{ result.result }}</p>
      <p v-if="result.reward">Ödül: {{ result.reward.title }} — {{ result.reward.description }}</p>
    </div>

    <p v-if="message" class="msg">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const businessCode = ref('')
const businessName = ref('')
const statusInfo = ref(null)
const games = ref([])
const message = ref('')
const loading = ref(false)
const result = ref(null)

// Geliştirme için örnek IP (admin panelinde verdiğin aralıkla uyumlu olsun)
const testIp = '192.168.2.42'

const detectBusiness = async () => {
  message.value = ''
  result.value = null
  try {
    loading.value = true
    const res = await fetch(`http://127.0.0.1:8000/api/where_am_i/?ip=${encodeURIComponent(testIp)}`, {
      credentials: 'include'
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'İşletme tespit edilemedi.')
    businessCode.value = data.unique_code
    businessName.value = data.business_name
  } catch (e) {
    message.value = e.message
  } finally {
    loading.value = false
  }
}

const loadGames = async () => {
  message.value = ''
  result.value = null
  games.value = []
  if (!businessCode.value) {
    message.value = 'Önce işletme kodu girin ya da Neredeyim? ile bulun.'
    return
  }
  loading.value = true
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/business_games/${encodeURIComponent(businessCode.value)}/`, {
      credentials: 'include'
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Oyun listesi alınamadı.')

    businessName.value = data.business_name
    games.value = data.games || []
  } catch (e) {
    message.value = e.message
  } finally {
    loading.value = false
  }
}

const loadStatus = async () => {
  message.value = ''
  statusInfo.value = null
  if (!businessCode.value) {
    message.value = 'Önce işletme kodu girin ya da Neredeyim? ile bulun.'
    return
  }
  loading.value = true
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/play_status/?unique_code=${encodeURIComponent(businessCode.value)}&ip=${encodeURIComponent(testIp)}`, {
      credentials: 'include'
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Durum alınamadı.')
    statusInfo.value = data
  } catch (e) {
    message.value = e.message
  } finally {
    loading.value = false
  }
}

const play = async (gameId) => {
  message.value = ''
  result.value = null
  if (!businessCode.value) {
    message.value = 'Önce işletme kodu girin.'
    return
  }
  loading.value = true
  try {
    const res = await fetch('http://127.0.0.1:8000/api/play_game/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        unique_code: businessCode.value,
        game_id: gameId,
        ip_address: testIp  // prod’da server gerçek IP’yi alacak
      })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Oyun oynanamadı.')
    result.value = data
    // Oynadıktan sonra statüyü güncelle
    await loadStatus()
  } catch (e) {
    message.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.wrap { max-width: 720px; margin: 2rem auto; color: #fff; }
.card { background: #1f1f1f; padding: 1rem; border-radius: 12px; margin: 1rem 0; }
.row { display: flex; gap: .75rem; align-items: center; justify-content: space-between; padding: .25rem 0; }
input { width: 100%; padding: .5rem; margin: .5rem 0; background: #2b2b2b; color: #fff; border: 1px solid #444; border-radius: 8px; }
button { padding: .5rem .9rem; border: 0; border-radius: 8px; background: #42b983; color: #111; cursor: pointer; }
button[disabled] { opacity: .6; cursor: not-allowed; }
.msg { color: #ffb3b3; }
</style>
