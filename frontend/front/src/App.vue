<template>
  <div id="app">
    <RouterView />
  </div>
</template>

<script setup>
// Vue Router View bileşeni router/index.js içindeki tanımlamalara göre yönlendirir
import { RouterView } from 'vue-router'
</script>

<style>
body {
  background-color: #121212;
  color: white;
  font-family: Arial, sans-serif;
  margin: 0;
  padding: 0;
}
</style>
