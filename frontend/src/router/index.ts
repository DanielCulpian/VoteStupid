import { createRouter, createWebHistory } from 'vue-router'
import PollView from '../views/PollView.vue'
import HomeView from '../views/HomeView.vue'
import CreatePollView from '../views/CreatePollView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/crear',
      name: 'create-poll',
      component: CreatePollView,
    },
    {
        path: '/votacion/:id',
        name: 'poll',
        component: PollView,
    },
  ],
})

export default router
