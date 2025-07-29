// src/router/index.js

import { createRouter, createWebHistory } from "vue-router";
import LoginForm from "../components/LoginForm.vue";
import GamePlayList from "../components/GamePlayList.vue";
import PlayGameForm from "../components/PlayGameForm.vue";

const routes = [
  { path: "/", component: LoginForm },
  { path: "/play", component: PlayGameForm },
  { path: "/gameplays", component: GamePlayList },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Şimdilik beforeEach'i kaldırıyoruz
// Gelecekte oturum süresi dolması gibi kontrol gerekiyorsa yeniden ekleriz

export default router;
