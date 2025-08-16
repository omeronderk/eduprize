<!-- src/components/ReportsPanel.vue -->
<template>
  <div class="reports-wrap">
    <!-- ÜST FİLTRELER -->
    <div class="filters">
      <div>
        <label>Başlangıç</label>
        <input type="date" v-model="start" />
      </div>
      <div>
        <label>Bitiş</label>
        <input type="date" v-model="end" />
      </div>
      <div>
        <label>Dönem</label>
        <select v-model="period">
          <option value="day">Gün</option>
          <option value="week">Hafta</option>
          <option value="month">Ay</option>
        </select>
      </div>
      <button @click="fetchSummary" :disabled="loadingSummary">Özeti Getir</button>
    </div>

    <!-- ÖZET TABLOSU -->
    <div class="card">
      <h3>Özet</h3>
      <div v-if="loadingSummary">Yükleniyor…</div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>Zaman</th>
            <th>Oynama</th>
            <th>Kazanma</th>
            <th>Kaybetme</th>
            <th>Tekil IP</th>
            <th>Tekil Oyuncu</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in summary" :key="row.bucket">
            <td>{{ fmt(row.bucket) }}</td>
            <td>{{ row.plays }}</td>
            <td>{{ row.wins }}</td>
            <td>{{ row.losses }}</td>
            <td>{{ row.unique_ips }}</td>
            <td>{{ row.unique_players }}</td>
          </tr>
          <tr v-if="summary.length === 0">
            <td colspan="6">Kayıt yok</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- KAYIT LİSTESİ FİLTRELERİ -->
    <div class="filters">
      <div>
        <label>Oyun ID</label>
        <input type="number" v-model.number="listFilters.game" placeholder="örn. 2" />
      </div>
      <div>
        <label>Kullanıcı</label>
        <input type="text" v-model="listFilters.user" placeholder="kullanıcı adı veya id" />
      </div>
      <div>
        <label>Sonuç</label>
        <select v-model="listFilters.result">
          <option value="">Tümü</option>
          <option value="win">Kazanma</option>
          <option value="loss">Kaybetme</option>
        </select>
      </div>
      <button @click="resetAndFetchList" :disabled="loadingList">Kayırları Getir</button>
    </div>

    <!-- KAYIT LİSTESİ -->
    <div class="card">
      <h3>Kayıtlar</h3>
      <div v-if="loadingList">Yükleniyor…</div>
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
          <tr v-for="it in list.items" :key="it.timestamp + it.ip">
            <td>{{ fmt(it.timestamp) }}</td>
            <td>{{ it.game }}</td>
            <td>{{ it.player || '-' }}</td>
            <td>{{ it.ip }}</td>
            <td>
              <span :class="it.result === 'win' ? 'pill green' : 'pill red'">
                {{ it.result === 'win' ? 'KAZANDI' : 'KAYBETTİ' }}
              </span>
            </td>
          </tr>
          <tr v-if="list.items.length === 0">
            <td colspan="5">Kayıt yok</td>
          </tr>
        </tbody>
      </table>

      <div class="pager" v-if="list.total > 0">
        <button :disabled="page<=1" @click="goto(page-1)">‹ Önceki</button>
        <span>Sayfa {{ page }} / {{ list.num_pages }}</span>
        <button :disabled="page>=list.num_pages" @click="goto(page+1)">Sonraki ›</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const toISO = (s) => {
  if (!s) return ''
  // zaten ISO ise bırak
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s
  // dd.MM.yyyy veya dd/MM/yyyy -> yyyy-mm-dd
  const m = s.match(/^(\d{2})[./](\d{2})[./](\d{4})$/)
  return m ? `${m[3]}-${m[2]}-${m[1]}` : s
}
const today = new Date()
const toYMD = (d) => d.toISOString().slice(0,10)
const sevenDaysAgo = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 7)

const start = ref(toYMD(sevenDaysAgo))
const end = ref(toYMD(today))
const period = ref('day')

const loadingSummary = ref(false)
const summary = ref([])

const fmt = (s) => {
  if (!s) return '-'
  // '2025-07-18T00:00:00+03:00' vb → daha okunur
  try { return new Date(s).toLocaleString() } catch { return s }
}

async function fetchSummary() {
  loadingSummary.value = true
  try {
    const url = new URL('http://127.0.0.1:8000/api/reports/summary/')
    url.searchParams.set('period', period.value)
    url.searchParams.set('start', toISO(start.value))
    url.searchParams.set('end', toISO(end.value))
    const res = await fetch(url, { credentials: 'include' })
    const data = await res.json()
    summary.value = data.data || []
  } finally {
    loadingSummary.value = false
  }
}

/* -------- Liste -------- */
const loadingList = ref(false)
const list = ref({ items: [], total: 0, num_pages: 1 })
const page = ref(1)
const pageSize = ref(25)
const listFilters = ref({
  game: '',
  user: '',
  result: '',
})

function resetAndFetchList() {
  page.value = 1
  fetchList()
}

async function fetchList() {
  loadingList.value = true
  try {
    const url = new URL('http://127.0.0.1:8000/api/reports/gameplays/')
    url.searchParams.set('start', start.value)
    url.searchParams.set('end', end.value)
    if (listFilters.value.game)  url.searchParams.set('game', String(listFilters.value.game))
    if (listFilters.value.user)  url.searchParams.set('user', listFilters.value.user)
    if (listFilters.value.result) url.searchParams.set('result', listFilters.value.result)
    url.searchParams.set('page', String(page.value))
    url.searchParams.set('page_size', String(pageSize.value))

    const res = await fetch(url, { credentials: 'include' })
    const data = await res.json()
    list.value = data
  } finally {
    loadingList.value = false
  }
}

function goto(p) {
  page.value = p
  fetchList()
}

/* ilk yükleme */
fetchSummary()
fetchList()
</script>

<style scoped>
.reports-wrap { display: grid; gap: 16px; }
.filters { display: flex; gap: 12px; align-items: end; flex-wrap: wrap; }
.filters label { display:block; font-size: 12px; opacity:.8; margin-bottom:4px; }
.filters input, .filters select { padding:6px 10px; background:#1b1b1b; color:#fff; border:1px solid #333; border-radius:6px; }
.filters button { padding:8px 12px; background:#2e7d32; border:none; border-radius:6px; color:#fff; }
.card { background:#151515; border:1px solid #2a2a2a; border-radius:10px; padding:12px; }
.table { width:100%; border-collapse: collapse; font-size:14px; }
.table th, .table td { border-bottom:1px solid #2a2a2a; padding:8px; text-align:left; }
.pager { display:flex; gap:12px; align-items:center; justify-content:flex-end; margin-top:10px; }
.pager button { padding:6px 10px; background:#333; color:#fff; border:none; border-radius:6px; }
.pill { padding:2px 8px; border-radius:999px; font-size:12px; }
.pill.green { background:#144d2a; color:#9be7a1; }
.pill.red   { background:#4d1414; color:#ffb4ab; }
</style>
