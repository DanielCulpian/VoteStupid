<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '../services/authService'

const password = ref('')
const error = ref('')
const busy = ref(false)
const route = useRoute()
const router = useRouter()

// Inicia sesión sin guardar la contraseña y permite únicamente redirecciones administrativas locales.
async function submit() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    await login(password.value)
    password.value = ''
    const target = String(route.query.redirect ?? '/admin')
    await router.replace(target.startsWith('/admin') && !target.startsWith('//') ? target : '/admin')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : 'No se ha podido iniciar sesión.' }
  finally { busy.value = false }
}
</script>
<template><main id="main-content" class="home" tabindex="-1"><header class="header"><RouterLink class="logo" to="/">VoteStupid<span>!</span></RouterLink><RouterLink to="/">Volver a las votaciones</RouterLink></header><section class="login-panel"><p class="eyebrow">ACCESO PRIVADO</p><h1>El espacio de quien organiza.</h1><p>Introduce la contraseña de administración para continuar.</p><form @submit.prevent="submit" :aria-busy="busy"><label for="admin-password">Contraseña</label><input id="admin-password" v-model="password" type="password" autocomplete="current-password" required maxlength="256" :disabled="busy" :aria-describedby="error ? 'login-error' : undefined" /><p v-if="error" id="login-error" class="error-message" role="alert">{{ error }}</p><button class="create-button" :disabled="busy">{{ busy ? 'Comprobando…' : 'Entrar en administración' }}</button></form></section></main></template>
