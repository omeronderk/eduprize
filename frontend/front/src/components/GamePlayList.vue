<template>
  <div>
    <h1>Oyun Kayıtları</h1>
    <ul>
      <li v-for="(item, index) in gameplays" :key="index">
        {{ item.game }} - {{ item.ip_address }} - {{ item.result }} - {{ item.timestamp }}
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'GamePlayList',
  data() {
    return {
      gameplays: []
    }
  },
  mounted() {
    fetch('http://127.0.0.1:8000/api/gameplays/')
      .then(response => response.json())
      .then(data => {
        this.gameplays = data;
      })
      .catch(error => {
        console.error('API hatası:', error);
      });
  }
}
</script>

<style scoped>
h1 {
  color: #4fc08d;
}
ul {
  list-style-type: none;
  padding: 0;
}
li {
  margin-bottom: 10px;
}
</style>
