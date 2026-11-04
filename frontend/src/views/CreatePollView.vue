<script setup lang="ts">
import { nextTick, ref } from 'vue'
import LiveAnnouncer from '../components/LiveAnnouncer.vue'
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
const invalidField = ref('')
const formAnnouncement = ref('')

// Anuncia el error de validación y lleva el foco al campo que necesita corrección.
async function showValidationError(message: string, fieldId: string) {
  errorMessage.value = message
  invalidField.value = fieldId
  await nextTick()
  document.getElementById(fieldId)?.focus()
}

// Añade una opción vacía al formulario de creación de votaciones.
async function addOption() {
  if (isSubmitting.value) return
  options.value.push('')
  formAnnouncement.value = `Opción ${options.value.length} añadida.`
  await nextTick()
  document.getElementById(`option-${options.value.length - 1}`)?.focus()
}

// Elimina una opción del formulario conservando al menos dos opciones.
async function removeOption(index: number) {
  if (isSubmitting.value || options.value.length <= 2) return
  options.value.splice(index, 1)
  formAnnouncement.value = `Opción ${index + 1} eliminada. Quedan ${options.value.length} opciones.`
  await nextTick()
  document.getElementById(`option-${Math.min(index, options.value.length - 1)}`)?.focus()
}

// Valida el formulario, crea la votación y prepara sus enlaces público y de administración.
async function submitPoll() {
  if (isSubmitting.value) return
  errorMessage.value = ''
  invalidField.value = ''
  createdPoll.value = null

  const cleanedOptions = options.value.map(option => option.trim())
  const selectionLimit = maxSelections.value === null || maxSelections.value === ''
    ? null
    : Number(maxSelections.value)

  if (!title.value.trim()) {
    await showValidationError('El título no puede estar vacío.', 'title')
    return
  }

  if (cleanedOptions.some(option => !option)) {
    await showValidationError('Todas las opciones deben tener texto.', `option-${cleanedOptions.findIndex(option => !option)}`)
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
    await showValidationError('El máximo de selecciones debe estar entre 1 y el número de opciones.', 'max-selections')
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
    await nextTick()
    document.getElementById('creation-success')?.focus()
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
  <main id="main-content" class="home" tabindex="-1">
    <LiveAnnouncer :message="isSubmitting ? 'Creando tu votación.' : createdPoll ? 'Votación creada correctamente. Guarda el enlace privado de administración.' : formAnnouncement" />
    <header class="header">
      <RouterLink class="logo" to="/">
        VoteStupid<span>!</span>
      </RouterLink>
    </header>

    <section class="form-container">
      <p class="eyebrow">NUEVA VOTACIÓN</p>
      <h1>Vamos a <span>decidir.</span></h1>

      <div v-if="createdPoll" class="success-message">
        <h2 id="creation-success" tabindex="-1">¡Votación creada!</h2>
        <p>Tu votación se ha guardado correctamente.</p>

        <div class="created-link">
          <h3>Enlace para los participantes</h3>
          <a :href="publicUrl" target="_blank" rel="noopener" aria-describedby="public-link-hint">
            {{ publicUrl }}
          </a>
          <p id="public-link-hint" class="field-hint">Se abre en una pestaña nueva.</p>
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
        <p class="field-hint">El título y las opciones de respuesta son obligatorios.</p>
        <label for="title">Título de la votación</label>
        <input
          id="title"
          :aria-invalid="invalidField === 'title'"
          :aria-describedby="invalidField === 'title' ? 'creation-error' : undefined"
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
            :aria-invalid="invalidField === 'max-selections'"
            :aria-describedby="invalidField === 'max-selections' ? 'max-selections-hint creation-error' : 'max-selections-hint'"
            :disabled="isSubmitting"
            v-model.number="maxSelections"
            type="number"
            min="1"
            :max="options.length"
            placeholder="Sin límite adicional"
          />
          <p id="max-selections-hint" class="field-hint">
            Si lo dejas vacío, no habrá un límite adicional.
          </p>
        </div>

        <div class="options-header">
          <h2 class="options-heading">Opciones de respuesta</h2>
          <span>{{ options.length }} opciones</span>
        </div>

        <div
          v-for="(_, index) in options"
          :key="index"
          class="option-row"
        >
          <input
            v-model="options[index]"
            :id="`option-${index}`"
            :aria-invalid="invalidField === `option-${index}`"
            :aria-describedby="invalidField === `option-${index}` ? 'creation-error' : undefined"
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

        <p v-if="errorMessage" id="creation-error" class="error-message" role="alert" aria-atomic="true">
          {{ errorMessage }}
        </p>

        <p v-if="isSubmitting" class="loading-message">Creando tu votación. Espera un momento...</p>

        <button
          class="create-button"
          type="submit"
          :disabled="isSubmitting"
        >
          {{ isSubmitting ? 'Creando...' : 'Crear votación' }}
          <span v-if="!isSubmitting" aria-hidden="true">→</span>
        </button>
      </form>
    </section>
  </main>
</template>
