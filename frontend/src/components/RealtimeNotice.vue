<script setup lang="ts">
import type { RealtimeConnectionState } from '../services/websocketService'

defineProps<{ state: RealtimeConnectionState; busy?: boolean }>()
defineEmits<{ reconnect: [] }>()
</script>

<template>
  <div v-if="state === 'connecting'" class="loading-message" role="status">
    Conectando con las actualizaciones en directo...
  </div>
  <div v-else-if="state === 'disconnected'" class="warning-message" role="status">
    <p>Se ha perdido la conexión en directo. Los resultados y el estado podrían no estar actualizados.</p>
    <button type="button" class="retry-button" :disabled="busy" @click="$emit('reconnect')">
      {{ busy ? 'Conectando...' : 'Volver a conectar' }}
    </button>
  </div>
</template>
