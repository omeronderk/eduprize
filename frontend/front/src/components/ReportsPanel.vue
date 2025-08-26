<!-- src/components/ReportsPanel.vue -->
<template>
  <div class="reports">
    <!-- Üst Filtre Satırı -->
    <div class="filters-row">
      <div class="filter">
        <label>Başlangıç</label>
        <input type="date" v-model="start" />
      </div>
      <div class="filter">
        <label>Bitiş</label>
        <input type="date" v-model="end" />
      </div>
      <div class="filter">
        <label>Dönem</label>
        <select v-model="period">
          <option value="day">Gün</option>
          <option value="week">Hafta</option>
          <option value="month">Ay</option>
        </select>
      </div>
      <div class="filter">
        <label>Sonuç</label>
        <select v-model="resultFilter">
          <option value="all">Tümü</option>
          <option value="won">Kazandı</option>
          <option value="lost">Kaybetti</option>
        </select>
      </div>
      <button class="btn" @click="refreshAll" :disabled="loadingSummary || loadingItems">Özeti Getir</button>
    </div>

    <!-- Özet kutuları -->
    <div class="summary">
      <div class="card">
        <div class="title">Oynama</div>
        <div class="value">{{ summary.played }}</div>
      </div>
      <div class="card">
        <div class="title">Kazanma</div>
        <div class="value">{{ summary.won }}</div>
      </div>
      <div class="card">
        <div class="title">Kaybetme</div>
        <div class="value">{{ summary.lost }}</div>
      </div>
      <div class="card">
        <div class="title">Tekil IP</div>
        <div class="value">{{ summary.unique_ip }}</div>
      </div>
      <div class="card">
        <div class="title">Tekil Oyuncu</div>
        <div class="value">{{ summary.unique_player }}</div>
      </div>
    </div>

    <p v-if="errorSummary" class="error">{{ errorSummary }}</p>

    <!-- Kayıtlar Filtreleri -->
    <div class="filters-row second">
      <div class="filter">
        <label>Oyun ID</label>
        <input type="text" placeholder="örn. 2" v-model="gameId" />
      </div>
      <div class="filter">
        <label>Kullanıcı</label>
        <input type="text" placeholder="kullanıcı adı veya id" v-model="username" />
      </div>
      <div class="filter">
        <label>Sayfa Boyutu</label>
        <select v-model.number="pageSize">
          <option :value="10">10</option>
          <option :value="25">25</option>
          <option :value="50">50</option>
        </select>
      </div>
      <button class="btn" @click="fetchItems" :disabled="loadingItems">Kayıtları Getir</button>
    </div>

    <p v-if="errorItems" class="error">{{ errorItems }}</p>

    <!-- Kayıtlar Tablosu -->
    <div class="table-wrap">
      <div v-if="loadingItems" class="loading">Yükleniyor…</div>

      <table v-else class="table">
        <thead>
          <tr>
            <th>Tarih</th>
            <th>Oyun</th>
            <th>Oyuncu</th>
            <th>IP</th>
            <th>Sonuç</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!items.length">
            <td colspan="5">Kayıt yok</td>
          </tr>
          <tr v-for="row in items" :key="row.id || row.timestamp + '-' + (row.ip_address || '')">
            <td>{{ formatTs(row.timestamp) }}</td>
            <td>{{ row.game_name || row.game || '-' }}</td>
            <td>{{ row.username || row.user || '-' }}</td>
            <td>{{ row.ip_address || '-' }}</td>
            <td>
              <span :class="row.result === true || row.result === 'won' ? 'pill won' : 'pill lost'">
                {{ (row.result === true || row.result === 'won') ? 'Kazandı' : 'Kaybetti' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Sayfalama -->
      <div class="pager" v-if="total > pageSize">
        <button class="btn" @click="prevPage" :disabled="page <= 1">Önceki</button>
        <span>Sayfa {{ page }} / {{ totalPages }}</span>
        <button class="btn" @click="nextPage" :disabled="page >= totalPages">Sonraki</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

/** ----------------- STATE ----------------- **/
const loadingSummary = ref(false)
const loadingItems = ref(false)
const errorSummary = ref('')
const errorItems = ref('')

const summary = ref({
  played: 0,
  won: 0,
  lost: 0,
  unique_ip: 0,
  unique_player: 0,
})

const items = ref([])
const page = ref(1)
const pageSize = ref(25)
const total = ref(0)

/** Filtreler */
const start = ref('')               // 'YYYY-MM-DD'
const end = ref('')                 // 'YYYY-MM-DD'
const period = ref('day')           // day|week|month
const resultFilter = ref('all')     // all|won|lost
const gameId = ref('')
const username = ref('')

/** ----------------- HELPERS ----------------- **/
function toIso(d, endOfDay = false) {
  if (!d) return ''
  return `${d}${endOfDay ? 'T23:59:59' : 'T00:00:00'}`
}

function formatTs(ts) {
  if (!ts) return '-'
  try {
    return new Date(ts).toLocaleString('tr-TR')
  } catch {
    return String(ts)
  }
}

async function doGet(url) {
  const res = await fetch(url, { credentials: 'include' })
  let data
  try {
    data = await res.json()
  } catch {
    throw new Error(`Beklenmeyen yanıt (JSON değil). HTTP ${res.status}`)
  }
  if (!res.ok) {
    throw new Error(data?.error || `HTTP ${res.status}`)
  }
  return data
}

/** ----------------- FETCHERS ----------------- **/
async function fetchSummary() {
  loadingSummary.value = true
  errorSummary.value = ''
  try {
    const qs = new URLSearchParams()
    if (start.value) qs.set('start', toIso(start.value, false))
    if (end.value)   qs.set('end',   toIso(end.value,   true))
    if (period.value) qs.set('period', period.value)
    if (resultFilter.value) qs.set('result', resultFilter.value)

    const url = `http://127.0.0.1:8000/api/reports/summary?${qs.toString()}`
    const data = await doGet(url)
    const s = data?.summary || {}
    summary.value = {
      played: Number(s.played ?? 0),
      won: Number(s.won ?? 0),
      lost: Number(s.lost ?? 0),
      unique_ip: Number(s.unique_ip ?? 0),
      unique_player: Number(s.unique_player ?? 0),
    }
  } catch (e) {
    errorSummary.value = String(e.message || e)
    summary.value = { played: 0, won: 0, lost: 0, unique_ip: 0, unique_player: 0 }
  } finally {
    loadingSummary.value = false
  }
}

async function fetchItems() {
  loadingItems.value = true
  errorItems.value = ''
  try {
    const qs = new URLSearchParams()
    if (start.value) qs.set('start', toIso(start.value, false))
    if (end.value)   qs.set('end',   toIso(end.value,   true))
    if (resultFilter.value) qs.set('result', resultFilter.value)
    if (gameId.value) qs.set('game_id', gameId.value)
    if (username.value) qs.set('username', username.value)
    qs.set('page', String(page.value))
    qs.set('page_size', String(pageSize.value))

    const url = `http://127.0.0.1:8000/api/reports/gameplays?${qs.toString()}`
    const data = await doGet(url)
    items.value = Array.isArray(data?.items) ? data.items : []
    total.value = Number(data?.total ?? 0)
    page.value = Number(data?.page ?? 1)
    pageSize.value = Number(data?.page_size ?? pageSize.value)
  } catch (e) {
    errorItems.value = String(e.message || e)
    items.value = []
    total.value = 0
  } finally {
    loadingItems.value = false
  }
}

async function refreshAll() {
  page.value = 1
  await Promise.all([fetchSummary(), fetchItems()])
}

/** ----------------- PAGINATION ----------------- **/
const totalPages = computed(() => {
  if (!total.value || !pageSize.value) return 1
  return Math.max(1, Math.ceil(total.value / pageSize.value))
})

function prevPage() {
  if (page.value > 1) {
    page.value -= 1
    fetchItems()
  }
}
function nextPage() {
  if (page.value < totalPages.value) {
    page.value += 1
    fetchItems()
  }
}

/** İlk yükleme */
onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.reports { color: #eaeaea; }
.filters-row {
  display: flex; gap: 12px; align-items: end; flex-wrap: wrap; margin: 10px 0 16px;
}
.filters-row.second { margin-top: 6px; }
.filter { display: flex; flex-direction: column; min-width: 160px; }
.filter label { font-size: 12px; color: #bdbdbd; margin-bottom: 6px; }

.btn {
  background: #2e7d32; border: none; color: white; padding: 8px 12px;
  border-radius: 6px; cursor: pointer;
}
.btn:disabled { opacity: .6; cursor: default; }

.summary {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px;
}
.card { background: #1e1e1e; border-radius: 10px; padding: 14px; text-align: center; }
.card .title { color: #9e9e9e; font-size: 12px; margin-bottom: 6px; }
.card .value { font-size: 22px; font-weight: 700; }

.table-wrap { background: #121212; border-radius: 8px; padding: 8px; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { border-bottom: 1px solid #2c2c2c; padding: 10px; text-align: left; font-size: 14px; }
.table th { color: #bdbdbd; font-weight: 600; }

.loading { padding: 14px; color: #bdbdbd; }

.pill { padding: 4px 8px; border-radius: 999px; font-size: 12px; }
.pill.won { background: #1b5e20; }
.pill.lost { background: #6d1b1b; }

.error { margin: 8px 0; color: #ef5350; }

.pager {
  display: flex; gap: 10px; align-items: center; justify-content: center;
  padding: 10px 0 2px;
}
</style>
