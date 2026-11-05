<script setup lang="ts">
import { nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// Keep the page title descriptive, including the initial home page load.
watch(() => route.meta.title, title => {
  document.title = `${String(title ?? 'Inicio')} | VoteStupid`
}, { immediate: true })

// Move focus to the main content when navigating between application views.
watch(() => route.path, async () => {
  await nextTick()
  document.getElementById('main-content')?.focus()
})
</script>

<template>
  <a class="skip-link" href="#main-content">Saltar al contenido principal</a>
  <RouterView :key="$route.path" />
</template>
