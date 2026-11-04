<script setup lang="ts">
import { useRoute } from 'vue-router'
import { getPoll } from '../services/pollService'
import { castVote, updateVote } from '../services/voteService'
import {
  getPollResults,
  type PollResults,
} from '../services/resultsService'
import type { PollResponse } from '../types/poll'
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
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

// Guarda las opciones del voto en el navegador para recuperarlas al volver a la votación.
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

// Carga los resultados de la votación y actualiza los indicadores de carga y error.
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

// Suscribe el estado y los resultados sin dejar que una conexión anterior cambie el aviso actual.
function connectLive() {
  if (!poll.value || isDisposed) return
  const version = ++connectionVersion
  socket?.close()
  try {
    socket = connectToPoll(
      poll.value.id,
      // Refleja los resultados recibidos y elimina errores de consultas anteriores.
      updatedResults => {
        if (version !== connectionVersion || isDisposed) return
        results.value = updatedResults as PollResults
        resultsError.value = ''
      },
      // Habilita o bloquea los controles cuando cambia el estado de la votación.
      isActive => {
        if (version === connectionVersion && !isDisposed && poll.value) {
          poll.value.is_active = isActive
          successMessage.value = ''
          statusAnnouncement.value = isActive
            ? 'La votación se ha reabierto. Puedes votar.'
            : 'La votación se ha cerrado. Ya no se pueden modificar los votos.'
        }
      },
      // Mantiene visible el estado de conexión de la suscripción actual.
      state => {
        if (version === connectionVersion && !isDisposed) connectionState.value = state
      },
      // Recupera los cambios perdidos sin alterar las opciones seleccionadas por el usuario.
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

// Reconecta el directo y recupera el estado y los resultados que pudieron cambiar durante el corte.
function reconnectLive() {
  if (!poll.value || isSubmitting.value || isDisposed) return
  connectLive()
}

// Carga la votación, recupera el voto local y permite reintentar si falla el enlace o el servidor.
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

// Cambia la selección de opciones solo si la votación está abierta.
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

// Obtiene el texto de una opción del ranking para sus etiquetas y anuncios accesibles.
function rankingOptionText(optionId: string): string {
  return poll.value?.options.find(option => option.id === optionId)?.text ?? 'Opción'
}

// Reordena el ranking, anuncia la nueva posición y mantiene el foco en la opción movida.
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

// Registra o actualiza el voto si la votación está abierta y no hay otro envío.
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
// Cierra el WebSocket al abandonar la vista para liberar la conexión.
onUnmounted(() => {
  isDisposed = true
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

        <!-- ELECCIÓN ÚNICA Y MÚLTIPLE -->
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

        <!-- MENSAJES -->
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

        <!-- BOTÓN DE VOTACIÓN -->
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

        <!-- RESULTADOS -->
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
