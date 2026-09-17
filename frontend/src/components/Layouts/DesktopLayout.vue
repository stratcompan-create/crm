<template>
  <div class="flex h-screen w-screen">
    <AppSidebar />
    <div class="flex-1 flex flex-col h-full overflow-auto bg-surface-base">
      <TopNav />
      <AppHeader />
      <div :key="$route.fullPath" class="page-fade-in flex flex-1 flex-col overflow-auto">
        <slot />
      </div>
    </div>
    <GlobalModals />
  </div>
</template>
<script setup>
import TopNav from '@/components/Layouts/TopNav.vue'
import AppSidebar from '@/components/Layouts/AppSidebar.vue'
import AppHeader from '@/components/Layouts/AppHeader.vue'
import GlobalModals from '@/components/Modals/GlobalModals.vue'

// $route is available here the same way App.vue already used it directly in
// its template with no import — Vue Router injects it as a global template
// property, not something this file needs to declare itself.
</script>

<style>
/* Recreating the DOM node on every route change (via :key) re-triggers this
   CSS animation automatically — no <Transition> needed, so it works even
   though page components render multiple root nodes (Transition requires a
   single root and silently breaks with fragments). */
.page-fade-in {
  animation: page-fade-in 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes page-fade-in {
  from {
    opacity: 0;
    transform: translateY(18px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
