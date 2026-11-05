<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import PollCatalog from '../components/PollCatalog.vue'
import { logout } from '../services/authService'
const router = useRouter()
const busy = ref(false)
const error = ref('')

// Revoke the session before leaving the private area and preserve any failure message.
async function signOut() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { await logout(); await router.replace('/acceso') }
  catch (cause) { error.value = cause instanceof Error ? cause.message : 'No se ha podido cerrar sesión.' }
  finally { busy.value = false }
}
</script>
<template><main id="main-content" class="home" tabindex="-1"><header class="header"><RouterLink class="logo" to="/">VoteStupid<span>!</span></RouterLink><nav class="private-nav" aria-label="Administración"><RouterLink to="/admin/crear">Crear votación</RouterLink><RouterLink to="/">Ver página pública</RouterLink><button type="button" :disabled="busy" @click="signOut">Cerrar sesión</button></nav></header><p class="eyebrow">ZONA PRIVADA</p><h1 class="dashboard-title">Aquí se organizan<br />las buenas decisiones.</h1><p v-if="error" class="error-message" role="alert">{{ error }}</p><PollCatalog administrative /></main></template>
