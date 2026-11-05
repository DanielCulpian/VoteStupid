<script setup lang="ts">
import PollCatalog from '../components/PollCatalog.vue'
</script>

<template>
  <main id="main-content" class="home" tabindex="-1">
    <header class="header">
      <a class="logo" href="/">VoteStupid<span>!</span></a>
      <a class="history-nav" href="#votaciones">Explorar votaciones</a>

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
        Las preguntas están sobre la mesa. Elige una votación,
        comparte tu opinión y descubre qué decide el grupo.
      </p>

      <a class="create-button" href="#votaciones">
        Encuentra tu próxima decisión
        <span aria-hidden="true">→</span>
      </a>

      <p class="note">Gratis · Anónimo · Sin necesidad de registrarse</p>
    </section>

    <PollCatalog />

    <footer class="footer">
      VoteStupid! © 2026
    </footer>
  </main>
</template>
