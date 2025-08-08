<template>
  <div class="login-form">
    <h2>Giriş Yap</h2>
    <form @submit.prevent="login">
      <label for="username">Kullanıcı Adı:</label>
      <input v-model="username" id="username" type="text" required />

      <label for="password">Şifre:</label>
      <input v-model="password" id="password" type="password" required />

      <button type="submit">Giriş</button>
    </form>
    <p v-if="message">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const username = ref('')
const password = ref('')
const message = ref('')

const login = async () => {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify({
        username: username.value,
        password: password.value
      })
    })

    const data = await response.json()

    if (response.ok) {
      const whoamiRes = await fetch('http://127.0.0.1:8000/api/whoami/', {
        method: 'GET',
        credentials: 'include'
      })
      const whoamiData = await whoamiRes.json()

      if (whoamiData.role === 'admin') {
        router.push('/admin-dashboard')
      } else if (whoamiData.role === 'business_user') {
        router.push('/business-dashboard')
      } else if (whoamiData.role === 'player') {
        router.push('/play')
      } else {
        message.value = 'Tanımsız rol. Erişim izniniz yok.'
      }

    } else {
      message.value = data.error || 'Giriş başarısız.'
    }
  } catch (err) {
    message.value = 'Sunucu hatası: ' + err.message
  }
}
</script>

<style scoped>
.login-form {
  max-width: 300px;
  margin: 2rem auto;
  padding: 1rem;
  border: 1px solid #ccc;
  border-radius: 5px;
  background-color: #1e1e1e;
  color: white;
}

.login-form label {
  display: block;
  margin-bottom: 0.25rem;
}

.login-form input {
  width: 100%;
  padding: 0.5rem;
  margin-bottom: 1rem;
}

button {
  width: 100%;
  padding: 0.5rem;
  background-color: #42b983;
  border: none;
  color: white;
  cursor: pointer;
}

button:hover {
  background-color: #36986a;
}
</style>
