<script setup lang="ts">
import { ref } from 'vue'
import { createPoll } from '../services/pollService'
import type {
  PollType,
  PollCreatedResponse,
} from '../types/poll'

const title = ref('')
const description = ref('')
const pollType = ref<PollType>('single_choice')
const options = ref(['', ''])
const maxSelections = ref<number | string | null>(null)
const closesAt = ref('')
const publicUrl = ref('')
const adminUrl = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')
const createdPoll = ref<PollCreatedResponse | null>(null)

// Añade una opción vacía al formulario de creación de votaciones.
function addOption() {
  if (isSubmitting.value) return
  options.value.push('')
}

// Elimina una opción del formulario conservando al menos dos opciones.
function removeOption(index: number) {
  if (isSubmitting.value || options.value.length <= 2) return
  options.value.splice(index, 1)
}

// Valida el formulario, crea la votación y prepara sus enlaces público y de administración.
async function submitPoll() {
  if (isSubmitting.value) return
  errorMessage.value = ''
  createdPoll.value = null

  const cleanedOptions = options.value.map(option => option.trim())
  const selectionLimit = maxSelections.value === null || maxSelections.value === ''
    ? null
    : Number(maxSelections.value)

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
    selectionLimit !== null &&
    (
      !Number.isInteger(selectionLimit) ||
      selectionLimit < 1 ||
      selectionLimit > cleanedOptions.length
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
          ? selectionLimit
          : null,
      closes_at: closesAt.value
        ? new Date(closesAt.value).toISOString()
        : null,
    })

    createdPoll.value = poll
    publicUrl.value =
      `${window.location.origin}/votacion/${poll.id}`

    adminUrl.value =
      `${window.location.origin}/admin/${poll.id}#token=${encodeURIComponent(poll.admin_token)}`
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

      <div v-if="createdPoll" class="success-message" role="status">
        <h2>¡Votación creada!</h2>
        <p>Tu votación se ha guardado correctamente.</p>

        <div class="created-link">
          <h3>Enlace para los participantes</h3>
          <a :href="publicUrl" target="_blank">
            {{ publicUrl }}
          </a>
        </div>

        <div class="created-link">
          <h3>Enlace privado de administración</h3>
          <a :href="adminUrl">
            Abrir panel de administración →
          </a>
          <p>
            Guarda este enlace. Cualquiera que lo tenga podrá administrar
            tu votación.
          </p>
        </div>
      </div>

      <form
        v-else
        class="poll-form"
        :aria-busy="isSubmitting"
        @submit.prevent="submitPoll"
      >
        <label for="title">Título de la votación</label>
        <input
          id="title"
          :disabled="isSubmitting"
          v-model="title"
          type="text"
          placeholder="Ej. ¿Dónde vamos a cenar?"
          required
        />

        <label for="description">Descripción (opcional)</label>
        <textarea
          id="description"
          :disabled="isSubmitting"
          v-model="description"
          placeholder="Añade un poco de contexto..."
          rows="3"
        />

        <label for="poll-type">Tipo de votación</label>
        <select id="poll-type" v-model="pollType" :disabled="isSubmitting">
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
            :disabled="isSubmitting"
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
            :disabled="isSubmitting"
            :aria-label="`Opción ${index + 1}`"
            type="text"
            :placeholder="`Opción ${index + 1}`"
            required
          />

          <button
            type="button"
            class="remove-button"
            :aria-label="`Eliminar opción ${index + 1}`"
            :disabled="isSubmitting || options.length <= 2"
            @click="removeOption(index)"
          >
            ×
          </button>
        </div>

        <button
          type="button"
          class="add-button"
          :disabled="isSubmitting"
          @click="addOption"
        >
          + Añadir opción
        </button>

        <label for="closes-at">Fecha de cierre (opcional)</label>
        <input
          id="closes-at"
          :disabled="isSubmitting"
          v-model="closesAt"
          type="datetime-local"
        />

        <p v-if="errorMessage" class="error-message" role="alert">
          {{ errorMessage }}
        </p>

        <p v-if="isSubmitting" class="loading-message" role="status">Creando tu votación. Espera un momento...</p>

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
