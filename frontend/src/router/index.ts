import { createRouter, createWebHistory } from 'vue-router'
import PollView from '../views/PollView.vue'
import HomeView from '../views/HomeView.vue'
import CreatePollView from '../views/CreatePollView.vue'
import AdminView from '../views/AdminView.vue'
import NotFoundView from '../views/NotFoundView.vue'
import HistoryView from '../views/HistoryView.vue'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'
import { getSession } from '../services/authService'

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
      path: '/crear', redirect: '/admin/crear',
    },
    { path: '/acceso', component: LoginView, meta: { title: 'Acceso privado' } },
    { path: '/admin', component: DashboardView, meta: { title: 'Administración', private: true } },
    {
      path: '/admin/crear',
      name: 'create-poll',
      meta: { title: 'Crear una votación', private: true },
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
      meta: { title: 'Administración', private: true },
      component: AdminView,
    },
    {
      path: '/historial', redirect: '/votaciones',
    },
    {
      path: '/votaciones',
      name: 'history',
      meta: { title: 'Votaciones' },
      component: HistoryView,
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      meta: { title: 'Página no encontrada' },
      component: NotFoundView,
    },
  ],
})

// Revalidate the cookie before entering a private route; URL tokens are not sessions.
router.beforeEach(async to => {
  if (!to.meta.private) return true
  try { await getSession(); return true }
  catch { return { path: '/acceso', query: { redirect: to.path } } }
})

// Leave the administrative view when the server reports an expired session.
window.addEventListener('admin-session-expired', () => {
  if (router.currentRoute.value.meta.private) void router.replace({ path: '/acceso', query: { redirect: router.currentRoute.value.path } })
})

export default router
