<script setup lang="ts">
import { useRoute } from 'vue-router'
import { getPoll } from '../services/pollService'
import { castVote, updateVote } from '../services/voteService'
import {
  getPollResults,
  type PollResults,
} from '../services/resultsService'
import type { PollResponse } from '../types/poll'
import { onMounted, onUnmounted, ref } from 'vue'
import { connectToPoll } from '../services/websocketService'

const route = useRoute()

const poll = ref<PollResponse | null>(null)
const results = ref<PollResults | null>(null)

const isLoading = ref(true)
const isLoadingResults = ref(false)
const isSubmitting = ref(false)

const errorMessage = ref('')
const resultsError = ref('')
const successMessage = ref('')

const selectedOptionIds = ref<string[]>([])
const rankingOptionIds = ref<string[]>([])
const hasVoted = ref(false)

let socket: WebSocket | null = null

// Guarda las opciones del voto en el navegador para recuperarlas al volver a la votación.
function saveVoteLocally(optionIds: string[]) {
  if (!poll.value) return

  localStorage.setItem(
    `votestupid:vote:${poll.value.id}`,
    JSON.stringify(optionIds),
  )
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

// Carga la votación, recupera el voto local y suscribe los cambios en directo al montar la vista.
onMounted(async () => {
  try {
    poll.value = await getPoll(String(route.params.id))

    if (poll.value) {
      socket = connectToPoll(
        poll.value.id,
        // Refleja los resultados recibidos sin recargar la vista.
        updatedResults => {
          results.value = updatedResults as PollResults
        },
        // Aplica el estado recibido para bloquear o habilitar los controles.
        isActive => {
          if (poll.value) {
            poll.value.is_active = isActive
          }
        },
      )
    }

    rankingOptionIds.value = poll.value.options.map(
      option => option.id,
    )

    const savedVote = localStorage.getItem(
      `votestupid:vote:${poll.value.id}`,
    )

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
        localStorage.removeItem(
          `votestupid:vote:${poll.value.id}`,
        )
      }
    }

    await loadResults()
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : 'No se ha podido cargar la votación.'
  } finally {
    isLoading.value = false
  }
})

// Cambia la selección de opciones solo si la votación está abierta.
function toggleOption(optionId: string) {
  if (!poll.value || !poll.value.is_active) return

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

// Reordena una opción del ranking solo si la votación está abierta.
function moveRanking(index: number, direction: number) {
  if (!poll.value?.is_active) return

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

  ;[updated[index], updated[newIndex]] = [
    updated[newIndex],
    updated[index],
  ]

  rankingOptionIds.value = updated
}

// Registra o actualiza el voto si la votación está abierta y no hay otro envío.
async function submitVote() {
  if (!poll.value || !poll.value.is_active || isSubmitting.value) return

  errorMessage.value = ''
  successMessage.value = ''

  const optionIds =
    poll.value.poll_type === 'ranking'
      ? rankingOptionIds.value
      : selectedOptionIds.value

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
  }
}
// Cierra el WebSocket al abandonar la vista para liberar la conexión.
onUnmounted(() => {
  socket?.close()
})
</script>

<template>
  <main class="home">
    <header class="header">
      <RouterLink class="logo" to="/">
        VoteStupid<span>!</span>
      </RouterLink>
    </header>

    <section class="form-container">
      <p class="eyebrow">VOTACIÓN</p>

      <div v-if="isLoading">
        Cargando votación...
      </div>

      <div
        v-else-if="errorMessage && !poll"
        class="error-message"
      >
        {{ errorMessage }}
      </div>

      <div v-else-if="poll">
        <h1>{{ poll.title }}</h1>

        <p v-if="poll.description">
          {{ poll.description }}
        </p>

        <p class="field-hint">
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
        >
          <button
            v-for="option in poll.options"
            :key="option.id"
            type="button"
            class="poll-option"
            :class="{
              selected: selectedOptionIds.includes(option.id),
            }"
            :disabled="!poll.is_active"
            @click="toggleOption(option.id)"
          >
            <span>{{ option.text }}</span>

            <span>
              {{ selectedOptionIds.includes(option.id) ? '✓' : '' }}
            </span>
          </button>
        </div>

        <!-- RANKING -->
        <div v-else class="poll-options">
          <div
            v-for="(optionId, index) in rankingOptionIds"
            :key="optionId"
            class="ranking-option"
          >
            <span>{{ index + 1 }}.</span>

            <span class="ranking-text">
              {{ poll.options.find(option => option.id === optionId)?.text }}
            </span>

            <button
              type="button"
              :disabled="!poll.is_active || index === 0"
              aria-label="Subir opción"
              @click="moveRanking(index, -1)"
            >
              ↑
            </button>

            <button
              type="button"
              :disabled="!poll.is_active || index === rankingOptionIds.length - 1"
              aria-label="Bajar opción"
              @click="moveRanking(index, 1)"
            >
              ↓
            </button>
          </div>
        </div>

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
          role="status"
        >
          {{ successMessage }}
        </p>

        <!-- BOTÓN DE VOTACIÓN -->
        <button
          v-if="poll.is_active"
          type="button"
          class="create-button"
          :disabled="isSubmitting"
          @click="submitVote"
        >
          {{
            isSubmitting
              ? 'Enviando voto...'
              : hasVoted
                ? 'Actualizar mi voto'
                : 'Enviar mi voto'
          }}

          <span v-if="!isSubmitting">→</span>
        </button>

        <p v-if="!poll.is_active" class="error-message">
          Esta votación está cerrada.
        </p>

        <!-- RESULTADOS -->
        <section class="results-section">
          <div class="results-header">
            <h2>Resultados</h2>

            <span v-if="results">
              {{ results.total_votes }} votos
            </span>
          </div>

          <p v-if="isLoadingResults">
            Cargando resultados...
          </p>

          <p
            v-else-if="resultsError"
            class="error-message"
          >
            {{ resultsError }}
          </p>

          <div v-else-if="results">
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

              <div class="result-bar">
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
