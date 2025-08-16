<template>
  <div class="wrap">
    <h1>İşletme Paneli</h1>

    <section class="card" v-if="summary">
      <h3>{{ summary.business.name }} ({{ summary.business.unique_code }})</h3>
      <div class="grid">
        <div class="kpi">
          <div class="kpi-title">Bugün Toplam</div>
          <div class="kpi-value">{{ summary.today.total }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-title">Kazanma</div>
          <div class="kpi-value">{{ summary.today.wins }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-title">Kaybetme</div>
          <div class="kpi-value">{{ summary.today.losses }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-title">Tekil IP</div>
          <div class="kpi-value">{{ summary.today.unique_ips }}</div>
        </div>
      </div>
      <small>Günlük IP başı limit: {{ summary.business.daily_game_limit_per_ip }}</small>
    </section>
    <button @click="$router.push('/business-reports')">Raporlar</button>
    <section class="card">
      <div class="row">
        <h3>Oyunlar & Olasılıklar</h3>
        <button @click="refresh" :disabled="loading">Yenile</button>
      </div>

      <table class="tbl" v-if="games.length">
        <thead>
          <tr>
            <th>Oyun</th>
            <th>Kazanma Olasılığı</th>
            <th>Bugün Oynama</th>
            <th>Bugün Kazanma</th>
            <th>Bugün Kaybetme</th>
            <th>İşlem</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in games" :key="g.business_game_id">
            <td>{{ g.game_name }}</td>
            <td>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                v-model.number="g.win_probability"
                class="num"
              />
            </td>
            <td>{{ g.plays_today }}</td>
            <td>{{ g.wins_today }}</td>
            <td>{{ g.losses_today }}</td>
            <td>
              <button @click="saveProb(g)" :disabled="loading">Kaydet</button>
              <button class="danger" @click="removeGame(g)" :disabled="loading">Kaldır</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-else class="empty">Henüz oyun ekli değil.</div>

      <div class="add-box">
        <h4>İşletmeye Oyun Ekle</h4>
        <label>Oyun ID</label>
        <input v-model.number="newGameId" type="number" min="1" class="num" placeholder="örn. 1" />
        <label>Kazanma Olasılığı (0..1)</label>
        <input v-model.number="newWinProb" type="number" step="0.01" min="0" max="1" class="num" placeholder="örn. 0.25" />
        <button @click="addGame" :disabled="loading">Ekle</button>
      </div>
    </section>

    <p v-if="message" class="msg">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const summary = ref(null)
const games = ref([])
const loading = ref(false)
const message = ref('')
const newGameId = ref(null)
const newWinProb = ref(0.2)

const fetchSummary = async () => {
  const res = await fetch('http://127.0.0.1:8000/api/business/summary/', { credentials: 'include' })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Özet alınamadı.')
  summary.value = data
  // per-game verileri buradan alıyoruz
  games.value = data.games || []
}

const refresh = async () => {
  message.value = ''
  loading.value = true
  try {
    await fetchSummary()
  } catch (e) {
    message.value = e.message
  } finally {
    loading.value = false
  }
}

const saveProb = async (g) => {
  message.value = ''
  loading.value = true
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/business/games/${g.business_game_id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ win_probability: g.win_probability })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Güncellenemedi.')
    message.value = 'Kazanma olasılığı güncellendi.'
  } catch (e) {
    message.value = e.message
  } finally {
    loading.value = false
  }
}

const removeGame = async (g) => {
  if (!confirm(`"${g.game_name}" işletmeden kaldırılsın mı?`)) return
  message.value = ''
  loading.value = true
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/business/games/${g.business_game_id}/`, {
      method: 'DELETE',
      credentials: 'include'
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.error || 'Silinemedi.')
    // listeden çıkar
    games.value = games.value.filter(x => x.business_game_id !== g.business_game_id)
    message.value = 'Oyun ilişkisi kaldırıldı.'
  } catch (e) {
    message.value = e.message
  } finally {
    loading.value = false
  }
}

const addGame = async () => {
  message.value = ''
  loading.value = true
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/business/games/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        game_id: newGameId.value,
        win_probability: newWinProb.value
      })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Eklenemedi.')
    message.value = 'Oyun işletmeye eklendi.'
    await refresh()
  } catch (e) {
    message.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.wrap { max-width: 1000px; margin: 1.5rem auto; color: #fff; }
.card { background: #1f1f1f; padding: 1rem; border-radius: 12px; margin: 1rem 0; }
.grid { display: grid; grid-template-columns: repeat(4,1fr); gap: .75rem; margin-top: .5rem; }
.kpi { background: #2a2a2a; padding: .75rem; border-radius: 10px; text-align: center; }
.kpi-title { font-size: .9rem; opacity: .8; }
.kpi-value { font-size: 1.4rem; font-weight: 700; }
.row { display: flex; align-items: center; justify-content: space-between; gap: .75rem; }
.tbl { width: 100%; border-collapse: collapse; margin-top: .75rem; }
.tbl th, .tbl td { border-bottom: 1px solid #333; padding: .5rem; text-align: left; }
.num { width: 120px; padding: .3rem .4rem; background: #2b2b2b; color: #fff; border: 1px solid #444; border-radius: 6px; }
.add-box { margin-top: 1rem; display: grid; gap: .35rem; grid-template-columns: 220px 220px 120px; align-items: end; }
.add-box h4 { grid-column: 1 / -1; margin: 0 0 .5rem 0; }
button { padding: .45rem .8rem; border-radius: 8px; background: #42b983; color: #111; border: 0; cursor: pointer; }
button.danger { background: #ff6b6b; }
.msg { margin-top: .5rem; color: #ffb3b3; }
.empty { opacity: .8; }
</style>
