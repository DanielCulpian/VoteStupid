<script setup lang="ts">
</script>

<template>
  <main id="main-content" class="home" tabindex="-1">
    <header class="header">
      <a class="logo" href="/">VoteStupid<span>!</span></a>
      <RouterLink class="history-nav" to="/historial">Histórico</RouterLink>

      <span class="tagline">Las decisiones importantes...</span>
    </header>

    <section class="hero">
      <p class="eyebrow">BIENVENIDO A VOTESTUPID</p>

      <h1>
        Porque decidir<br />
        entre amigos<br />
        es <span>complicado.</span>
      </h1>

      <p class="description">
        Crea votaciones, comparte el enlace y deja que tus amigos
        decidan. Sin registros y sin complicaciones.
      </p>

      <RouterLink class="create-button" to="/crear">
        Crear una votación
        <span aria-hidden="true">→</span>
      </RouterLink>

      <p class="note">Gratis · Anónimo · Sin necesidad de registrarse</p>
    </section>

    <footer class="footer">
      VoteStupid! © 2026
    </footer>
  </main>
</template>
