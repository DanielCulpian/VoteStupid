<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import LiveAnnouncer from '../components/LiveAnnouncer.vue'
import { getPoll } from '../services/pollService'
import { getAdminPoll } from '../services/adminService'
import { ApiError } from '../services/api'
import {
  getPollHistory, hasSessionAdminAccess, parsePrivatePollLink, rememberPoll,
  type PollHistoryEntry,
} from '../services/historyService'

interface HistoryRow {
  poll: PollHistoryEntry
  availability: 'cached' | 'current' | 'missing' | 'unavailable'
  canAdminister: boolean
}

const rows = ref<HistoryRow[]>([])
const isLoading = ref(false)
const isImporting = ref(false)
const storageWarning = ref('')
const refreshWarning = ref('')
const privateLink = ref('')
const importError = ref('')
const importSuccess = ref('')
let isDisposed = false

// Lee la lista local y actualiza solo sus identificadores mediante el endpoint público existente.
async function loadHistory() {
  if (isLoading.value) return
  const restoreFocus = document.activeElement?.id === 'history-refresh'
  isLoading.value = true
  storageWarning.value = ''
  refreshWarning.value = ''
  try {
    rows.value = getPollHistory().map(poll => ({
      poll, availability: 'cached', canAdminister: hasSessionAdminAccess(poll.id),
    }))
    // Limita las consultas simultáneas para que un histórico largo no sature el servidor.
    for (let offset = 0; offset < rows.value.length; offset += 5) {
      if (isDisposed) return
      await Promise.all(rows.value.slice(offset, offset + 5).map(async row => {
        // Conserva la entrada local si el servidor está apagado o la votación no está disponible.
        try {
          const poll = await getPoll(row.poll.id)
          if (isDisposed) return
          row.poll = poll
          row.availability = 'current'
          try {
            rememberPoll(poll)
          } catch (error) {
            storageWarning.value = error instanceof Error ? error.message : 'No se ha podido guardar el histórico.'
          }
        } catch (error) {
          if (isDisposed) return
          row.availability = error instanceof ApiError && error.status === 404 ? 'missing' : 'unavailable'
          refreshWarning.value = 'No se han podido actualizar todas las votaciones. Las entradas sin conexión conservan sus últimos datos guardados; puedes volver a intentarlo.'
        }
      }))
    }
  } catch (error) {
    storageWarning.value = error instanceof Error ? error.message : 'No se ha podido leer el histórico.'
  } finally {
    isLoading.value = false
    await nextTick()
    if (restoreFocus && (document.activeElement === document.body || document.activeElement?.id === 'history-refresh')) {
      document.getElementById('history-refresh')?.focus()
    }
  }
}

// Verifica el token con el backend antes de recuperar una votación y habilitar su administración en esta sesión.
async function recoverPoll() {
  if (isImporting.value || isLoading.value) return
  isImporting.value = true
  importError.value = ''
  importSuccess.value = ''
  try {
    const { id, token } = parsePrivatePollLink(privateLink.value, window.location.origin)
    const poll = await getAdminPoll(id, token)
    if (isDisposed) return
    try {
      sessionStorage.setItem(`votestupid:admin-token:${id}`, token)
    } catch {
      throw new Error('No se puede conservar el acceso en esta sesión. Abre directamente tu enlace privado de administración.')
    }
    rememberPoll(poll)
    privateLink.value = ''
    await loadHistory()
    importSuccess.value = 'Votación recuperada. El acceso de administración está disponible durante esta sesión.'
    await nextTick()
    document.getElementById(`history-${poll.id}`)?.focus()
  } catch (error) {
    importError.value = error instanceof Error ? error.message : 'No se ha podido recuperar la votación.'
  } finally {
    isImporting.value = false
    await nextTick()
    if (importError.value && !isDisposed) document.getElementById('private-poll-link')?.focus()
  }
}

// Muestra una fecha legible con la zona horaria del dispositivo.
function formatDate(value: string): string {
  return new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

// Traduce el tipo de votación almacenado a su nombre en la interfaz.
function pollTypeLabel(type: PollHistoryEntry['poll_type']): string {
  return { single_choice: 'Elección única', multiple_choice: 'Elección múltiple', ranking: 'Ranking' }[type]
}

// Distingue el cierre manual del vencimiento por fecha, sin presentar datos almacenados como actuales.
function pollStatus(poll: PollHistoryEntry): string {
  if (!poll.is_active) return 'Cerrada'
  if (poll.closes_at && Date.parse(poll.closes_at) <= Date.now()) return 'Cerrada por fecha'
  return 'Abierta'
}

onMounted(loadHistory)

// Impide que una consulta pendiente modifique la vista después de abandonarla.
onUnmounted(() => { isDisposed = true })
</script>

<template>
  <main id="main-content" class="home" tabindex="-1">
    <LiveAnnouncer :message="isImporting ? 'Comprobando el enlace privado.' : importSuccess || (isLoading ? 'Actualizando el histórico.' : `Histórico cargado: ${rows.length} votaciones.`)" />
    <header class="header">
      <RouterLink class="logo" to="/">VoteStupid<span>!</span></RouterLink>
      <RouterLink class="history-nav" to="/crear">Crear una votación</RouterLink>
    </header>
    <section class="form-container history-container">
      <p class="eyebrow">TUS VOTACIONES</p>
      <h1>Histórico de votaciones</h1>
      <p>Consulta tus votaciones anteriores y sus resultados, también cuando estén cerradas.</p>
      <p class="field-hint">
        Esta lista se guarda solo en este navegador; las votaciones y sus resultados se conservan en el servidor.
        Si cambias de navegador o borras sus datos, puedes recuperar tus votaciones con sus enlaces privados.
        Cualquier persona que utilice este mismo perfil del navegador podrá ver esta lista.
      </p>
      <button id="history-refresh" class="retry-button history-refresh" type="button" :disabled="isLoading || isImporting" @click="loadHistory">
        {{ isLoading ? 'Actualizando...' : 'Actualizar histórico' }}
      </button>
      <p v-if="isLoading" class="loading-message">Comprobando el estado de tus votaciones...</p>
      <p v-if="storageWarning" class="warning-message" role="alert">{{ storageWarning }}</p>
      <p v-if="refreshWarning" class="warning-message" role="status">{{ refreshWarning }}</p>
      <p v-if="!isLoading && rows.length === 0 && !storageWarning" class="history-empty">
        Todavía no hay votaciones guardadas en este navegador. Crea una nueva o recupera una anterior con su enlace privado.
      </p>

      <ul class="history-list" role="list" aria-label="Votaciones guardadas en este navegador">
        <li v-for="row in rows" :key="row.poll.id" class="admin-card history-card">
          <h2 :id="`history-${row.poll.id}`" tabindex="-1">{{ row.poll.title }}</h2>
          <dl class="history-details">
            <div><dt>Tipo</dt><dd>{{ pollTypeLabel(row.poll.poll_type) }}</dd></div>
            <div><dt>Creación</dt><dd><time :datetime="row.poll.created_at">{{ formatDate(row.poll.created_at) }}</time></dd></div>
            <div><dt>{{ row.availability === 'current' ? 'Estado' : 'Último estado guardado' }}</dt><dd>{{ pollStatus(row.poll) }}</dd></div>
          </dl>
          <p v-if="row.availability === 'missing'" class="warning-message">Esta votación no se encuentra en el servidor actual. Su entrada sigue guardada en este navegador.</p>
          <p v-else-if="row.availability === 'unavailable'" class="field-hint">Sin conexión: no se ha podido comprobar su estado actual.</p>
          <div class="history-actions">
            <RouterLink class="retry-button" :to="`/votacion/${row.poll.id}`" :aria-label="`Ver votación y resultados: ${row.poll.title}`">Ver votación y resultados</RouterLink>
            <RouterLink v-if="row.canAdminister" class="retry-button" :to="`/admin/${row.poll.id}`" :aria-label="`Administrar: ${row.poll.title}`">Abrir administración</RouterLink>
          </div>
          <p v-if="!row.canAdminister" class="field-hint">Para administrar esta votación, recupera abajo su enlace privado. El histórico no guarda tokens permanentemente.</p>
        </li>
      </ul>

      <section class="admin-card" aria-labelledby="recover-heading">
        <h2 id="recover-heading">Recuperar una votación anterior</h2>
        <p>Introduce el enlace privado que guardaste al crearla. Comprobaremos el token antes de añadirla al histórico.</p>
        <form class="poll-form" :aria-busy="isImporting" @submit.prevent="recoverPoll">
          <label for="private-poll-link">Enlace privado de administración</label>
          <input id="private-poll-link" v-model="privateLink" type="password" autocomplete="off" :spellcheck="false" required :disabled="isImporting || isLoading" :aria-invalid="Boolean(importError)" :aria-describedby="importError ? 'private-link-hint history-import-error' : 'private-link-hint'" />
          <p id="private-link-hint" class="field-hint">El enlace completo incluye el token después de #token=. Solo se conserva en esta sesión.</p>
          <p v-if="importError" id="history-import-error" class="error-message" role="alert">{{ importError }}</p>
          <p v-if="importSuccess" class="success-message">{{ importSuccess }}</p>
          <button class="create-button" type="submit" :disabled="isImporting || isLoading">{{ isImporting ? 'Comprobando...' : 'Recuperar votación' }}</button>
        </form>
      </section>
    </section>
  </main>
</template>
