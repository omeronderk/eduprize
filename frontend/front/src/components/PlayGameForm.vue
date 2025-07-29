<template>
  <div>
    <h2>Oyun Oyna</h2>
    <form @submit.prevent="submitForm">
      <div>
        <label>İşletme Kodu:</label>
        <input v-model="form.unique_code" required />
      </div>
      <div>
        <label>Oyun ID:</label>
        <input v-model="form.game_id" required />
      </div>
      <div>
        <label>IP Adresi:</label>
        <input v-model="form.ip_address" required />
      </div>
      <button type="submit">Oyna</button>
    </form>

    <div v-if="result" style="margin-top: 20px">
      <h3>Sonuç</h3>
      <p>{{ result }}</p>
    </div>
  </div>
</template>

<script>
export default {
  name: "PlayGameForm",
  data() {
    return {
      form: {
        unique_code: "",
        game_id: "",
        ip_address: ""
      },
      result: ""
    };
  },
  methods: {
    async submitForm() {
      try {
        const response = await fetch("http://127.0.0.1:8000/api/play_game/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(this.form)
        });

        const data = await response.json();

        if (!response.ok) {
          this.result = data.error || "Hata oluştu.";
        } else {
          this.result = data.result + (data.reward ? ` | Ödül: ${data.reward.title}` : "");
        }
      } catch (err) {
        this.result = "Sunucu hatası: " + err.message;
      }
    }
  }
};
</script>

<style scoped>
form div {
  margin-bottom: 10px;
}
input {
  padding: 5px;
}
button {
  padding: 5px 10px;
}
</style>
