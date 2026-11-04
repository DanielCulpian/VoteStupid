
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import type { PollResponse } from '../types/poll'
import type { PollResults } from '../services/resultsService'
import { getAdminPoll, closePoll, reopenPoll } from '../services/adminService'
import { getPollResults } from '../services/resultsService'
import { connectToPoll, type RealtimeConnectionState } from '../services/websocketService'
import RealtimeNotice from '../components/RealtimeNotice.vue'

const route = useRoute()
const pollId = String(route.params.id)

const poll = ref<PollResponse | null>(null)
const results = ref<PollResults | null>(null)
const adminToken = ref('')

let pollSocket: WebSocket | null = null
let connectionVersion = 0
let isDisposed = false

const isLoading = ref(false)
const isUpdating = ref(false)
const isLoadingResults = ref(false)
const resultsError = ref('')
const connectionState = ref<RealtimeConnectionState>('connecting')
const errorMessage = ref('')
const successMessage = ref('')

// Carga los resultados por separado para que un fallo no oculte la administración.
async function loadResults() {
  isLoadingResults.value = true
  resultsError.value = ''
  try {
    results.value = await getPollResults(pollId)
  } catch (error) {
    resultsError.value = error instanceof Error ? error.message : 'No se han podido cargar los resultados.'
  } finally {
    isLoadingResults.value = false
  }
}

// Conecta las actualizaciones y descarta los avisos de una suscripción anterior.
function connectLive() {
  if (isDisposed) return
  const version = ++connectionVersion
  pollSocket?.close()
  try {
    pollSocket = connectToPoll(
      pollId,
      // Refleja los resultados recibidos y retira el error de carga anterior.
      updatedResults => {
        if (version !== connectionVersion || isDisposed) return
        results.value = updatedResults as PollResults
        resultsError.value = ''
      },
      // Sincroniza también los cambios realizados desde otro panel de administración.
      isActive => {
        if (version === connectionVersion && !isDisposed && poll.value) {
          if (poll.value.is_active !== isActive && !isUpdating.value) {
            successMessage.value = ''
          }
          poll.value.is_active = isActive
        }
      },
      // Informa de la conexión o desconexión del WebSocket actual.
      state => {
        if (version === connectionVersion && !isDisposed) connectionState.value = state
      },
    )
  } catch {
    connectionState.value = 'disconnected'
  }
}

// Recupera el token privado, carga la votación y sus resultados y conecta las actualizaciones en directo.
async function loadAdminPanel() {
  if (isLoading.value || isUpdating.value) return
  isLoading.value = true
  errorMessage.value = ''

  try {
    const storageKey = `votestupid:admin-token:${pollId}`

    const tokenFromUrl = new URLSearchParams(
      window.location.hash.slice(1),
    ).get('token')

    if (tokenFromUrl) {
      sessionStorage.setItem(storageKey, tokenFromUrl)

      window.history.replaceState(
        null,
        '',
        window.location.pathname + window.location.search,
      )
    }

    const savedToken = sessionStorage.getItem(storageKey)

    if (!savedToken) {
      throw new Error(
        'El enlace privado de administración está incompleto. Abre el enlace completo que recibiste al crear la votación.',
      )
    }

    adminToken.value = savedToken

    poll.value = await getAdminPoll(pollId, savedToken)
    if (isDisposed) return
    connectLive()
    await loadResults()
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : 'No se pudo cargar el panel de administración.'
  } finally {
    isLoading.value = false
  }
}

// Cierra o reabre la votación y actualiza los datos del panel de administración.
async function updatePollStatus() {
  if (!poll.value || !adminToken.value || isUpdating.value || isLoading.value) return

  isUpdating.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    if (poll.value.is_active) {
      poll.value = await closePoll(pollId, adminToken.value)
      successMessage.value = 'La votación se ha cerrado.'
    } else {
      poll.value = await reopenPoll(pollId, adminToken.value)
      successMessage.value = 'La votación se ha reabierto.'
    }

    await loadResults()
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : 'No se pudo actualizar la votación.'
  } finally {
    isUpdating.value = false
  }
}

const publicUrl = `${window.location.origin}/votacion/${pollId}`

// Copia el enlace público de la votación al portapapeles e informa del resultado.
async function copyPublicLink() {
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await navigator.clipboard.writeText(publicUrl)
    successMessage.value = 'Enlace público copiado.'
  } catch {
    errorMessage.value = `No se ha podido copiar el enlace. Puedes copiarlo manualmente: ${publicUrl}`
  }
}

onMounted(loadAdminPanel)

// Cierra el WebSocket al abandonar la vista para liberar la conexión.
onUnmounted(() => {
  isDisposed = true
  connectionVersion++
  pollSocket?.close()
  pollSocket = null
})
</script>

<template>
  <main class="admin-page">
    <nav class="header" aria-label="Navegación principal">
      <RouterLink class="logo" to="/">VoteStupid<span>!</span></RouterLink>
    </nav>
    <header>
      <h1>Panel de administración</h1>
      <p>Gestiona tu votación desde aquí.</p>
    </header>

    <p v-if="isLoading" class="loading-message" role="status" aria-busy="true">Cargando panel de administración...</p>

    <section v-else-if="errorMessage && !poll" class="error-message" role="alert">
      <p>{{ errorMessage }}</p>
      <button type="button" class="retry-button" @click="loadAdminPanel">Volver a intentar</button>
    </section>

    <template v-else-if="poll">
      <RealtimeNotice :state="connectionState" :busy="isUpdating || isLoading" @reconnect="loadAdminPanel" />
      <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
      <section class="admin-card">
        <h2>{{ poll.title }}</h2>
        <p v-if="poll.description">{{ poll.description }}</p>

        <p>
          Estado:
          <strong>
            {{ poll.is_active ? 'Abierta' : 'Cerrada' }}
          </strong>
        </p>

        <div class="admin-actions">
          <button
            type="button"
            :disabled="isUpdating"
            :aria-busy="isUpdating"
            @click="updatePollStatus"
          >
            {{
              isUpdating
                ? 'Actualizando...'
                : poll.is_active
                  ? 'Cerrar votación'
                  : 'Reabrir votación'
            }}
          </button>

          <button type="button" @click="copyPublicLink">
            Copiar enlace público
          </button>
        </div>
      </section>

      <p v-if="isUpdating" class="loading-message" role="status">Guardando el estado de la votación...</p>
      <p v-if="successMessage" class="success-message" role="status">
        {{ successMessage }}
      </p>

      <section class="admin-card">
        <h2>Resultados</h2>
        <p v-if="isLoadingResults" class="loading-message" role="status">Cargando resultados...</p>
        <div v-else-if="resultsError" class="error-message" role="alert">
          <p>{{ resultsError }}</p>
          <p v-if="results">Se muestran los últimos resultados recibidos.</p>
          <button type="button" class="retry-button" @click="loadResults">Volver a cargar resultados</button>
        </div>
        <template v-if="results">
          <p>Participantes: {{ results.total_votes }}</p>

          <div
            v-for="result in results.results"
            :key="result.option_id"
            class="result-row"
          >
            <div class="result-label">
              <strong>{{ result.option_text }}</strong>
              <span>{{ result.votes }} votos</span>
            </div>
            <div class="result-bar">
              <div
                class="result-bar-fill"
                :style="{ width: `${result.percentage}%` }"
              />
            </div>
            <p class="result-percentage">
              {{ result.percentage.toFixed(1) }}%
              <span v-if="poll.poll_type === 'ranking'">
                · {{ result.points }} puntos
              </span>
            </p>
          </div>
        </template>
      </section>
    </template>
  </main>
</template>
