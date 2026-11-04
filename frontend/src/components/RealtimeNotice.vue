<script setup lang="ts">
import type { RealtimeConnectionState } from '../services/websocketService'

defineProps<{ state: RealtimeConnectionState; busy?: boolean }>()
defineEmits<{ reconnect: [] }>()
</script>

<template>
  <p class="sr-only" role="status" aria-atomic="true">
    {{ state === 'connecting' ? 'Conectando con las actualizaciones en directo.' : state === 'disconnected' ? 'Se ha perdido la conexión en directo. Puedes volver a conectar.' : 'Conexión en directo disponible.' }}
  </p>
  <div v-if="state === 'connecting'" class="loading-message">
    Conectando con las actualizaciones en directo...
  </div>
  <div v-else-if="state === 'disconnected'" class="warning-message">
    <p>Se ha perdido la conexión en directo. Los resultados y el estado podrían no estar actualizados.</p>
    <button type="button" class="retry-button" :disabled="busy" @click="$emit('reconnect')">
      {{ busy ? 'Conectando...' : 'Volver a conectar' }}
    </button>
  </div>
</template>
