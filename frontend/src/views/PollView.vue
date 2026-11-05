<script setup lang="ts">
import { useRoute } from 'vue-router'
import { getPoll } from '../services/pollService'
import { castVote, updateVote } from '../services/voteService'
import {
  getPollResults,
  type PollResults,
} from '../services/resultsService'
import type { PollResponse } from '../types/poll'
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { connectToPoll, type RealtimeConnectionState, type PollConnection } from '../services/websocketService'
import RealtimeNotice from '../components/RealtimeNotice.vue'
import LiveAnnouncer from '../components/LiveAnnouncer.vue'

const route = useRoute()

const poll = ref<PollResponse | null>(null)
const results = ref<PollResults | null>(null)

const isLoading = ref(false)
const isLoadingResults = ref(false)
const isSubmitting = ref(false)

const errorMessage = ref('')
const resultsError = ref('')
const successMessage = ref('')
const storageWarning = ref('')
const connectionState = ref<RealtimeConnectionState>('connecting')
const rankingAnnouncement = ref('')
const statusAnnouncement = ref('')

const selectedOptionIds = ref<string[]>([])
const rankingOptionIds = ref<string[]>([])
const hasVoted = ref(false)

let socket: PollConnection | null = null
let connectionVersion = 0
let isDisposed = false
let deadlineTimer: ReturnType<typeof setTimeout> | undefined

// Disable controls when the deadline expires, even without a new server event.
function scheduleDeadline() {
  clearTimeout(deadlineTimer)
  if (!poll.value?.is_active || !poll.value.closes_at || isDisposed) return
  const remaining = Date.parse(poll.value.closes_at) - Date.now()
  if (remaining <= 0) {
    poll.value.is_active = false
    statusAnnouncement.value = 'La votación ha alcanzado su fecha de cierre.'
  } else {
    deadlineTimer = setTimeout(scheduleDeadline, Math.min(remaining, 2147483647))
  }
}

const stopDeadline = watch(() => poll.value?.closes_at, scheduleDeadline)

// Store the selected vote options in the browser for future visits.
function saveVoteLocally(optionIds: string[]) {
  if (!poll.value) return

  try {
    localStorage.setItem(
      `votestupid:vote:${poll.value.id}`,
      JSON.stringify(optionIds),
    )
  } catch {
    storageWarning.value = 'Tu voto se ha guardado, pero este navegador no permite recordarlo para tu próxima visita.'
  }
}

// Load poll results and update loading and error indicators.
async function loadResults() {
  if (!poll.value) return

  isLoadingResults.value = true
  resultsError.value = ''

  try {
    results.value = await getPollResults(poll.value.id)
  } catch (error) {
    resultsError.value =
      error instanceof Error
        ? error.message
        : 'No se han podido cargar los resultados.'
  } finally {
    isLoadingResults.value = false
  }
}

// Subscribe to state and results without letting older connections change the current notice.
function connectLive() {
  if (!poll.value || isDisposed) return
  const version = ++connectionVersion
  socket?.close()
  try {
    socket = connectToPoll(
      poll.value.id,
      // Apply received results and clear errors from earlier queries.
      updatedResults => {
        if (version !== connectionVersion || isDisposed) return
        results.value = updatedResults as PollResults
        resultsError.value = ''
      },
      // Enable or disable controls when the poll state changes.
      isActive => {
        if (version === connectionVersion && !isDisposed && poll.value) {
          poll.value.is_active = isActive
          successMessage.value = ''
          statusAnnouncement.value = isActive
            ? 'La votación se ha reabierto. Puedes votar.'
            : 'La votación se ha cerrado. Ya no se pueden modificar los votos.'
        }
      },
      // Keep the connection status visible for the current subscription.
      state => {
        if (version === connectionVersion && !isDisposed) connectionState.value = state
      },
      // Recover missed changes without altering the user's selected options.
      async isCurrent => {
        if (isDisposed || version !== connectionVersion || !isCurrent()) return
        const id = String(route.params.id)
        const [currentPoll, currentResults] = await Promise.all([getPoll(id), getPollResults(id)])
        if (isDisposed || version !== connectionVersion || !isCurrent()) return
        poll.value = currentPoll
        results.value = currentResults
        resultsError.value = ''
        statusAnnouncement.value = currentPoll.is_active ? 'La votación está abierta.' : 'La votación está cerrada.'
      },
    )
  } catch {
    connectionState.value = 'disconnected'
  }
}

// Reconnect live updates and recover state and results missed during the interruption.
function reconnectLive() {
  if (!poll.value || isSubmitting.value || isDisposed) return
  connectLive()
}

// Load the poll, restore the local vote, and allow retrying failed links or requests.
async function loadPoll() {
  if (isLoading.value) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    poll.value = await getPoll(String(route.params.id))
    if (isDisposed) return

    rankingOptionIds.value = poll.value.options.map(
      option => option.id,
    )

    let savedVote: string | null = null
    try {
      savedVote = localStorage.getItem(`votestupid:vote:${poll.value.id}`)
    } catch {
      storageWarning.value = 'Este navegador no permite recuperar tu voto anterior. Si ya has votado, utiliza el mismo navegador y permite el almacenamiento local.'
    }

    if (savedVote) {
      try {
        const savedIds: unknown = JSON.parse(savedVote)

        if (
          Array.isArray(savedIds) &&
          savedIds.every(
            id =>
              typeof id === 'string' &&
              poll.value!.options.some(
                option => option.id === id,
              ),
          )
        ) {
          selectedOptionIds.value = savedIds
          hasVoted.value = true

          if (poll.value.poll_type === 'ranking') {
            rankingOptionIds.value = savedIds
          }
        }
      } catch {
        storageWarning.value = 'No se ha podido recuperar el voto guardado en este navegador.'
      }
    }

    await loadResults()
    connectLive()
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : 'No se ha podido cargar la votación.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadPoll)

// Change selected options only while the poll is open.
function toggleOption(optionId: string) {
  if (!poll.value || !poll.value.is_active || isSubmitting.value) return

  successMessage.value = ''
  errorMessage.value = ''

  const selected = selectedOptionIds.value

  if (selected.includes(optionId)) {
    selectedOptionIds.value = selected.filter(
      id => id !== optionId,
    )
    return
  }

  if (poll.value.poll_type === 'single_choice') {
    selectedOptionIds.value = [optionId]
    return
  }

  if (
    poll.value.max_selections !== null &&
    selected.length >= poll.value.max_selections
  ) {
    errorMessage.value =
      `Solo puedes seleccionar ${poll.value.max_selections} opciones.`
    return
  }

  selectedOptionIds.value = [...selected, optionId]
}

// Retrieve ranking option text for accessible labels and announcements.
function rankingOptionText(optionId: string): string {
  return poll.value?.options.find(option => option.id === optionId)?.text ?? 'Opción'
}

// Reorder the ranking, announce its new position, and keep focus on the moved option.
async function moveRanking(index: number, direction: number) {
  if (!poll.value?.is_active || isSubmitting.value) return

  const newIndex = index + direction

  if (
    newIndex < 0 ||
    newIndex >= rankingOptionIds.value.length
  ) {
    return
  }

  successMessage.value = ''
  errorMessage.value = ''

  const updated = [...rankingOptionIds.value]
  const movedOptionId = updated[index]!

  ;[updated[index], updated[newIndex]] = [
    updated[newIndex],
    updated[index],
  ]

  rankingOptionIds.value = updated
  rankingAnnouncement.value = `${rankingOptionText(movedOptionId)}. Posición ${newIndex + 1} de ${updated.length}.`
  await nextTick()
  if (isDisposed) return
  const action = direction < 0 ? 'up' : 'down'
  const alternateAction = direction < 0 ? 'down' : 'up'
  const preferred = document.getElementById(`ranking-${movedOptionId}-${action}`) as HTMLButtonElement | null
  const alternate = document.getElementById(`ranking-${movedOptionId}-${alternateAction}`) as HTMLButtonElement | null
  if (preferred && !preferred.disabled) preferred.focus()
  else alternate?.focus()
}

// Create or update the vote only while the poll is open and no submission is pending.
async function submitVote() {
  if (!poll.value || !poll.value.is_active || isSubmitting.value) return
  const restoreFocus = document.activeElement?.id === 'submit-vote'

  errorMessage.value = ''
  successMessage.value = ''

  const optionIds = [...(
    poll.value.poll_type === 'ranking'
      ? rankingOptionIds.value
      : selectedOptionIds.value
  )]

  if (optionIds.length === 0) {
    errorMessage.value = 'Selecciona al menos una opción.'
    return
  }

  isSubmitting.value = true

  try {
    if (hasVoted.value) {
      await updateVote(poll.value.id, optionIds)

      successMessage.value = '¡Tu voto se ha actualizado!'
    } else {
      await castVote(poll.value.id, optionIds)

      successMessage.value =
        '¡Tu voto se ha registrado correctamente!'
    }

    hasVoted.value = true
    saveVoteLocally(optionIds)

    await loadResults()
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : 'No se ha podido guardar tu voto.'
  } finally {
    isSubmitting.value = false
    await nextTick()
    if (restoreFocus && (document.activeElement === document.body || document.activeElement?.id === 'submit-vote')) {
      document.getElementById(poll.value?.is_active ? 'submit-vote' : 'poll-closed')?.focus()
    }
  }
}
// Close the WebSocket when leaving the view to release the connection.
onUnmounted(() => {
  isDisposed = true
  stopDeadline()
  clearTimeout(deadlineTimer)
  connectionVersion++
  socket?.close()
})
</script>

<template>
  <main id="main-content" class="home" tabindex="-1">
    <LiveAnnouncer :message="isSubmitting ? 'Guardando tu voto.' : successMessage || rankingAnnouncement" />
    <LiveAnnouncer :message="statusAnnouncement" />
    <header class="header">
      <RouterLink class="logo" to="/">
        VoteStupid<span>!</span>
      </RouterLink>
    </header>

    <section class="form-container">
      <p class="eyebrow">VOTACIÓN</p>
      <h1 v-if="!poll">Votación</h1>

      <div v-if="isLoading" class="loading-message" role="status" aria-busy="true">
        Cargando votación...
      </div>

      <div
        v-else-if="errorMessage && !poll"
        class="error-message"
        role="alert"
      >
        <p>{{ errorMessage }}</p>
        <button type="button" class="retry-button" @click="loadPoll">Volver a intentar</button>
      </div>

      <div v-else-if="poll">
        <h1 id="page-title" tabindex="-1">{{ poll.title }}</h1>

        <RealtimeNotice
          :state="connectionState"
          :busy="isSubmitting"
          @reconnect="reconnectLive"
        />
        <p v-if="storageWarning" class="warning-message" role="status">{{ storageWarning }}</p>

        <p v-if="poll.description">
          {{ poll.description }}
        </p>

        <p id="vote-instructions" class="field-hint">
          <span v-if="poll.poll_type === 'single_choice'">
            Elige una opción.
          </span>

          <span v-else-if="poll.poll_type === 'multiple_choice'">
            Puedes elegir varias opciones.
          </span>

          <span v-else>
            Ordena las opciones de tu favorita a la menos favorita.
          </span>
        </p>

        <!-- SINGLE AND MULTIPLE CHOICE -->
        <div
          v-if="poll.poll_type !== 'ranking'"
          class="poll-options"
          role="group"
          aria-labelledby="vote-instructions"
        >
          <button
            v-for="option in poll.options"
            :key="option.id"
            type="button"
            class="poll-option"
            :class="{
              selected: selectedOptionIds.includes(option.id),
            }"
            :disabled="!poll.is_active || isSubmitting"
            :aria-pressed="selectedOptionIds.includes(option.id)"
            @click="toggleOption(option.id)"
          >
            <span>{{ option.text }}</span>

            <span aria-hidden="true">
              {{ selectedOptionIds.includes(option.id) ? '✓' : '' }}
            </span>
          </button>
        </div>

        <!-- RANKING -->
        <ol v-else class="poll-options ranking-list" role="list" aria-label="Orden de preferencia" aria-describedby="vote-instructions">
          <li
            v-for="(optionId, index) in rankingOptionIds"
            :key="optionId"
            class="ranking-option"
          >
            <span aria-hidden="true">{{ index + 1 }}.</span>

            <span class="ranking-text">
              {{ rankingOptionText(optionId) }}
            </span>

            <button
              type="button"
              :id="`ranking-${optionId}-up`"
              :disabled="!poll.is_active || isSubmitting || index === 0"
              :aria-label="`Subir ${rankingOptionText(optionId)}`"
              @click="moveRanking(index, -1)"
            >
              ↑
            </button>

            <button
              type="button"
              :id="`ranking-${optionId}-down`"
              :disabled="!poll.is_active || isSubmitting || index === rankingOptionIds.length - 1"
              :aria-label="`Bajar ${rankingOptionText(optionId)}`"
              @click="moveRanking(index, 1)"
            >
              ↓
            </button>
          </li>
        </ol>

        <!-- MESSAGES -->
        <p
          v-if="errorMessage"
          class="error-message"
          role="alert"
        >
          {{ errorMessage }}
        </p>

        <p
          v-if="successMessage"
          class="success-message"
        >
          {{ successMessage }}
        </p>

        <!-- VOTE BUTTON -->
        <p v-if="isSubmitting" class="loading-message">Guardando tu voto...</p>
        <button
          v-if="poll.is_active"
          id="submit-vote"
          type="button"
          class="create-button"
          :disabled="isSubmitting"
          :aria-busy="isSubmitting"
          @click="submitVote"
        >
          {{
            isSubmitting
              ? 'Enviando voto...'
              : hasVoted
                ? 'Actualizar mi voto'
                : 'Enviar mi voto'
          }}

          <span v-if="!isSubmitting" aria-hidden="true">→</span>
        </button>

        <p v-if="!poll.is_active" id="poll-closed" class="warning-message" tabindex="-1">
          Esta votación está cerrada.
        </p>

        <!-- RESULTS -->
        <section class="results-section">
          <div class="results-header">
            <h2>Resultados</h2>

            <span v-if="results" aria-live="polite" aria-atomic="true">
              {{ results.total_votes }} votos
            </span>
          </div>

          <p v-if="isLoadingResults" class="loading-message" role="status">
            Cargando resultados...
          </p>

          <div
            v-else-if="resultsError"
            class="error-message"
            role="alert"
          >
            <p>{{ resultsError }}</p>
            <p v-if="results">Se muestran los últimos resultados recibidos.</p>
            <button type="button" class="retry-button" @click="loadResults">Volver a cargar resultados</button>
          </div>

          <div v-if="results">
            <div
              v-for="result in results.results"
              :key="result.option_id"
              class="result-row"
            >
              <div class="result-label">
                <strong>{{ result.option_text }}</strong>

                <span>
                  {{ result.votes }} votos
                </span>
              </div>

              <div class="result-bar" aria-hidden="true">
                <div
                  class="result-bar-fill"
                  :style="{
                    width: `${result.percentage}%`,
                  }"
                />
              </div>

              <p class="result-percentage">
                {{ result.percentage.toFixed(1) }}%

                <span v-if="poll.poll_type === 'ranking'">
                  · {{ result.points }} puntos
                </span>
              </p>
            </div>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>
