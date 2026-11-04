import { createRouter, createWebHistory } from 'vue-router'
import PollView from '../views/PollView.vue'
import HomeView from '../views/HomeView.vue'
import CreatePollView from '../views/CreatePollView.vue'
import AdminView from '../views/AdminView.vue'
import NotFoundView from '../views/NotFoundView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      meta: { title: 'Inicio' },
      component: HomeView,
    },
    {
      path: '/crear',
      name: 'create-poll',
      meta: { title: 'Crear una votación' },
      component: CreatePollView,
    },
    {
        path: '/votacion/:id',
        name: 'poll',
        meta: { title: 'Votación' },
        component: PollView,
    },
    {
      path: '/admin/:id',
      name: 'admin',
      meta: { title: 'Administración' },
      component: AdminView,
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      meta: { title: 'Página no encontrada' },
      component: NotFoundView,
    },
  ],
})

export default router
