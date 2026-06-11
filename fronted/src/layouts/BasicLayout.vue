<template>
  <a-layout class="basic-layout">

    <GlobalHeader />

    <a-layout-content class="main-content">
      <!-- 路由切换动画 -->
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </a-layout-content>

    <GlobalFooter />

  </a-layout>
</template>

<script setup>
import GlobalHeader from './GlobalHeader.vue';
import GlobalFooter from './GlobalFooter.vue';
</script>

<style scoped>
.basic-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}

/* 可爱的切页动画 */
.fade-slide-enter-active, .fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1);
}
.fade-slide-enter-from { opacity: 0; transform: translateY(10px); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-10px); }
</style>
