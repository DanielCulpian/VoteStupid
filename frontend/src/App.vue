<script setup lang="ts">
import { nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// Mantiene un título descriptivo también en la primera carga de la portada.
watch(() => route.meta.title, title => {
  document.title = `${String(title ?? 'Inicio')} | VoteStupid`
}, { immediate: true })

// Sitúa el foco en el contenido al navegar entre vistas de la aplicación.
watch(() => route.path, async () => {
  await nextTick()
  document.getElementById('main-content')?.focus()
})
</script>

<template>
  <a class="skip-link" href="#main-content">Saltar al contenido principal</a>
  <RouterView :key="$route.path" />
</template>
