
<script setup lang="ts">
import { ref } from 'vue'
import { createPoll } from '../services/pollService'
import type { PollType, PollResponse } from '../types/poll'

const title = ref('')
const description = ref('')
const pollType = ref<PollType>('single_choice')
const options = ref(['', ''])
const maxSelections = ref<number | null>(null)
const closesAt = ref('')

const isSubmitting = ref(false)
const errorMessage = ref('')
const createdPoll = ref<PollResponse | null>(null)

function addOption() {
  options.value.push('')
}

function removeOption(index: number) {
  if (options.value.length <= 2) return
  options.value.splice(index, 1)
}

async function submitPoll() {
  errorMessage.value = ''
  createdPoll.value = null

  const cleanedOptions = options.value.map(option => option.trim())

  if (!title.value.trim()) {
    errorMessage.value = 'El título no puede estar vacío.'
    return
  }

  if (cleanedOptions.some(option => !option)) {
    errorMessage.value = 'Todas las opciones deben tener texto.'
    return
  }

  if (
    pollType.value === 'multiple_choice' &&
    maxSelections.value !== null &&
    (
      !Number.isInteger(maxSelections.value) ||
      maxSelections.value < 1 ||
      maxSelections.value > cleanedOptions.length
    )
  ) {
    errorMessage.value =
      'El máximo de selecciones debe estar entre 1 y el número de opciones.'
    return
  }

  isSubmitting.value = true

  try {
    const poll = await createPoll({
      title: title.value.trim(),
      description: description.value.trim() || null,
      poll_type: pollType.value,
      option_texts: cleanedOptions,
      max_selections:
        pollType.value === 'multiple_choice'
          ? maxSelections.value
          : null,
      closes_at: closesAt.value
        ? new Date(closesAt.value).toISOString()
        : null,
    })

    createdPoll.value = poll
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : 'No se ha podido crear la votación.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="home">
    <header class="header">
      <RouterLink class="logo" to="/">
        VoteStupid<span>!</span>
      </RouterLink>
    </header>

    <section class="form-container">
      <p class="eyebrow">NUEVA VOTACIÓN</p>
      <h1>Vamos a <span>decidir.</span></h1>

      <div v-if="createdPoll" class="success-message">
        <h2>¡Votación creada!</h2>
        <p>Tu votación se ha guardado correctamente.</p>
        <p class="poll-id">
          Identificador: {{ createdPoll.id }}
        </p>
        <RouterLink
            class="create-button"
            :to="`/votacion/${createdPoll.id}`"
            >
                Ver mi votación
            <span>→</span>
        </RouterLink>
      </div>

      <form
        v-else
        class="poll-form"
        @submit.prevent="submitPoll"
      >
        <label for="title">Título de la votación</label>
        <input
          id="title"
          v-model="title"
          type="text"
          placeholder="Ej. ¿Dónde vamos a cenar?"
          required
        />

        <label for="description">Descripción (opcional)</label>
        <textarea
          id="description"
          v-model="description"
          placeholder="Añade un poco de contexto..."
          rows="3"
        />

        <label for="poll-type">Tipo de votación</label>
        <select id="poll-type" v-model="pollType">
          <option value="single_choice">Elección única</option>
          <option value="multiple_choice">Selección múltiple</option>
          <option value="ranking">Ranking</option>
        </select>

        <div v-if="pollType === 'multiple_choice'">
          <label for="max-selections">
            Máximo de opciones seleccionables (opcional)
          </label>
          <input
            id="max-selections"
            v-model.number="maxSelections"
            type="number"
            min="1"
            :max="options.length"
            placeholder="Sin límite adicional"
          />
          <p class="field-hint">
            Si lo dejas vacío, no habrá un límite adicional.
          </p>
        </div>

        <div class="options-header">
          <label>Opciones de respuesta</label>
          <span>{{ options.length }} opciones</span>
        </div>

        <div
          v-for="(_, index) in options"
          :key="index"
          class="option-row"
        >
          <input
            v-model="options[index]"
            type="text"
            :placeholder="`Opción ${index + 1}`"
            required
          />

          <button
            type="button"
            class="remove-button"
            :disabled="options.length <= 2"
            @click="removeOption(index)"
          >
            ×
          </button>
        </div>

        <button
          type="button"
          class="add-button"
          @click="addOption"
        >
          + Añadir opción
        </button>

        <label for="closes-at">Fecha de cierre (opcional)</label>
        <input
          id="closes-at"
          v-model="closesAt"
          type="datetime-local"
        />

        <p v-if="errorMessage" class="error-message" role="alert">
          {{ errorMessage }}
        </p>

        <button
          class="create-button"
          type="submit"
          :disabled="isSubmitting"
        >
          {{ isSubmitting ? 'Creando...' : 'Crear votación' }}
          <span v-if="!isSubmitting">→</span>
        </button>
      </form>
    </section>
  </main>
</template>
