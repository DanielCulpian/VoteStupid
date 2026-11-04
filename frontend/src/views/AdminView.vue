
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import type { PollResponse } from '../types/poll'
import type { PollResults } from '../services/resultsService'
import { getAdminPoll, closePoll, reopenPoll } from '../services/adminService'
import { getPollResults } from '../services/resultsService'
import { connectToPoll } from '../services/websocketService'

const route = useRoute()
const pollId = String(route.params.id)

const poll = ref<PollResponse | null>(null)
const results = ref<PollResults | null>(null)
const adminToken = ref('')

let pollSocket: WebSocket | null = null

const isLoading = ref(true)
const isUpdating = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

async function loadAdminPanel() {
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
        'No se ha encontrado el enlace privado de administración.',
      )
    }

    adminToken.value = savedToken

    poll.value = await getAdminPoll(pollId, savedToken)
    results.value = await getPollResults(pollId)
    pollSocket = connectToPoll(pollId, updatedResults => {
      results.value = updatedResults as PollResults
    })
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : 'No se pudo cargar el panel de administración.'
  } finally {
    isLoading.value = false
  }
}

async function updatePollStatus() {
  if (!poll.value || !adminToken.value) return

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

    results.value = await getPollResults(pollId)
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

async function copyPublicLink() {
  try {
    await navigator.clipboard.writeText(publicUrl)
    successMessage.value = 'Enlace público copiado.'
  } catch {
    errorMessage.value = 'No se pudo copiar el enlace.'
  }
}

onMounted(loadAdminPanel)

onUnmounted(() => {
  pollSocket?.close()
  pollSocket = null
})
</script>

<template>
  <main class="admin-page">
    <header>
      <h1>Panel de administración</h1>
      <p>Gestiona tu votación desde aquí.</p>
    </header>

    <p v-if="isLoading">Cargando panel...</p>

    <section v-else-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </section>

    <template v-else-if="poll">
      <section class="admin-card">
        <h2>{{ poll.title }}</h2>
        <p v-if="poll.description">{{ poll.description }}</p>

        <p>
          Estado:
          <strong>
            {{ poll.is_active ? 'Abierta' : 'Cerrada' }}
          </strong>
        </p>

        <button
          type="button"
          :disabled="isUpdating"
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
      </section>

      <p v-if="successMessage" class="success-message">
        {{ successMessage }}
      </p>

      <section v-if="results" class="admin-card">
        <h2>Resultados</h2>
        <p>Participantes: {{ results.total_votes }}</p>

        <ul>
          <li
            v-for="result in results.results"
            :key="result.option_id"
          >
            {{ result.option_text }}:
            {{ result.votes }} votos
            ({{ result.percentage.toFixed(1) }} %)
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>
