<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getCatalog, isOpen, typeLabel, type PollCard } from '../services/catalogService'
import { connectToPoll, type PollConnection, type RealtimeConnectionState } from '../services/websocketService'
import RealtimeNotice from './RealtimeNotice.vue'

const props = defineProps<{ administrative?: boolean }>()
const state = ref('all')
const type = ref('')
const items = ref<PollCard[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const connectionState = ref<RealtimeConnectionState>('connecting')
let socket: PollConnection | null = null
let version = 0
let disposed = false
let timer: ReturnType<typeof setTimeout> | undefined
let expiry: ReturnType<typeof setTimeout> | undefined
const filtered = computed(() => state.value !== 'all' || type.value !== '')

// Descarta respuestas antiguas y conserva las tarjetas al fallar una actualización.
async function load(more = false, isCurrent = () => true) {
  if (disposed) return
  const requestVersion = ++version
  loading.value = true
  error.value = ''
  try {
    const page = await getCatalog(state.value, type.value, more ? items.value.length : 0, props.administrative)
    if (disposed || requestVersion !== version || !isCurrent()) return
    items.value = [...new Map((more ? [...items.value, ...page.items] : page.items).map(poll => [poll.id, poll])).values()]
    total.value = page.total
    scheduleExpiry()
  } catch (cause) {
    if (!disposed && requestVersion === version && isCurrent()) error.value = cause instanceof Error ? cause.message : 'No se pueden cargar las votaciones.'
    throw cause
  } finally {
    if (!disposed && requestVersion === version) loading.value = false
  }
}

// Evita rechazos sin gestionar en acciones iniciadas por la interfaz.
function refresh() { void load().catch(() => {}) }

// Agrupa eventos de estado consecutivos para no duplicar peticiones.
function queueRefresh() {
  clearTimeout(timer)
  timer = setTimeout(refresh, 200)
}

// Sustituye el transporte actual y cancela sus reintentos antes de reconectar manualmente.
function reconnect() {
  socket?.close()
  if (disposed) return
  socket = connectToPoll('catalog', () => {}, queueRefresh, value => { connectionState.value = value }, async valid => {
    if (valid() && !disposed) await load(false, valid)
  })
}

// Actualiza las tarjetas cuando alcanza su fecha de cierre aunque no haya un evento nuevo.
function scheduleExpiry() {
  clearTimeout(expiry)
  const dates = items.value.filter(p => p.is_active && p.closes_at && Date.parse(p.closes_at) > Date.now()).map(p => Date.parse(p.closes_at!))
  if (dates.length) expiry = setTimeout(refresh, Math.min(2147483647, Math.max(50, Math.min(...dates) - Date.now() + 50)))
}

// Restablece conjuntamente los filtros sin recargar la página.
function clearFilters() { state.value = 'all'; type.value = '' }

// Mantiene una sola suscripción y recupera el catálogo después de cada reconexión.
onMounted(() => {
  refresh()
  reconnect()
})
// Evita presentar tarjetas de otro filtro cuando la nueva consulta falla.
const stopFilters = watch([state, type], () => { items.value = []; total.value = 0; refresh() })
// Cancela respuestas pendientes, temporizadores y suscripción al abandonar el catálogo.
onUnmounted(() => { disposed = true; version++; stopFilters(); socket?.close(); clearTimeout(timer); clearTimeout(expiry) })
</script>

<template>
  <section id="votaciones" class="catalog" aria-labelledby="catalog-title" :aria-busy="loading">
    <div class="catalog-heading"><div><p class="eyebrow">ELIGE · PARTICIPA · DECIDE</p><h2 id="catalog-title">{{ administrative ? 'Tus votaciones, bajo control.' : 'Cada opinión cuenta.' }}</h2></div><p>Las activas primero.<br />Las decisiones, entre todos.</p></div>
    <div class="catalog-filters">
      <div><label for="catalog-state">Estado</label><select id="catalog-state" v-model="state"><option value="all">Todas</option><option value="active">Activas</option><option value="inactive">Inactivas</option></select></div>
      <div><label for="catalog-type">Tipo de votación</label><select id="catalog-type" v-model="type"><option value="">Todos los tipos</option><option value="single_choice">Elección única</option><option value="multiple_choice">Elección múltiple</option><option value="ranking">Ranking</option></select></div>
      <button type="button" :disabled="!filtered" @click="clearFilters">Limpiar filtros</button>
    </div>
    <RealtimeNotice :state="connectionState" :busy="loading" @reconnect="reconnect" />
    <p v-if="loading" role="status">Cargando votaciones…</p>
    <div v-if="error" class="error-message" role="alert"><p>{{ error }}</p><button type="button" @click="refresh">Volver a intentar</button></div>
    <p v-if="!loading && !error" class="catalog-count" role="status">{{ total }} {{ total === 1 ? 'votación disponible' : 'votaciones disponibles' }}</p>
    <div v-if="!loading && !error && !items.length" class="catalog-empty"><h3>{{ filtered ? 'No hay coincidencias.' : 'Las próximas decisiones empiezan aquí.' }}</h3><p>{{ filtered ? 'Prueba otros filtros para encontrar una votación.' : 'Todavía no hay votaciones publicadas. Vuelve pronto.' }}</p><button v-if="filtered" type="button" @click="clearFilters">Ver todas las votaciones</button></div>
    <ul class="poll-grid" role="list">
      <li v-for="poll in items" :key="poll.id" class="poll-card" :class="{ 'poll-card-closed': !isOpen(poll) }">
        <div class="poll-card-top"><span class="type-chip">{{ typeLabel(poll.poll_type) }}</span><span class="status-chip" :class="{ active: isOpen(poll) }"><span aria-hidden="true">●</span> {{ isOpen(poll) ? 'Activa' : 'Finalizada' }}</span></div>
        <h3>{{ poll.title }}</h3><p v-if="poll.description" class="poll-card-description">{{ poll.description }}</p>
        <time :datetime="poll.created_at">{{ new Date(poll.created_at).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' }) }}</time>
        <RouterLink :to="`/votacion/${poll.id}`" class="poll-card-link" :aria-label="`${isOpen(poll) ? 'Participar en' : 'Ver resultados de'} ${poll.title}`">{{ isOpen(poll) ? 'Participar' : 'Ver resultados' }}<span aria-hidden="true">↗</span></RouterLink>
        <RouterLink v-if="administrative" :to="`/admin/${poll.id}`" class="history-nav" :aria-label="`Administrar ${poll.title}`">Gestionar votación</RouterLink>
      </li>
    </ul>
    <button v-if="items.length < total" type="button" :disabled="loading" @click="load(true).catch(() => {})">Cargar más votaciones</button>
  </section>
</template>
