<template>
  <div id="app">
    <HeaderNav />
    <RouterView />
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router'
import HeaderNav from './components/HeaderNav.vue'
</script>

<style>
body {
  background-color: #121212;
  color: white;
  font-family: Arial, sans-serif;
  margin: 0; padding: 0;
}
</style>
