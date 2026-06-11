<template>
  <a-config-provider :theme="antdTheme">
    <div id="app" :class="themeMode">
      <router-view />
    </div>
  </a-config-provider>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { theme } from 'ant-design-vue';

// 主题状态：light 或 dark
const themeMode = ref('light');

// 监听全局主题切换事件
onMounted(() => {
  const savedTheme = localStorage.getItem('theme') || 'light';
  themeMode.value = savedTheme;
  document.documentElement.setAttribute('data-theme', savedTheme);

  window.addEventListener('theme-change', (e) => {
    themeMode.value = e.detail;
    localStorage.setItem('theme', e.detail);
    document.documentElement.setAttribute('data-theme', e.detail);
  });
});

// 动态计算 Ant Design 主题配置
const antdTheme = computed(() => ({
  algorithm: themeMode.value === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
  token: {
    colorPrimary: themeMode.value === 'dark' ? '#E76F51' : '#F4A261',
    borderRadius: 16,
    fontFamily: "'Jiangcheng', 'Quicksand', sans-serif",
  },
}));
</script>

<style>
/* 字体声明 */
@font-face {
  font-family: 'Daimeng';
  src: url('@/assets/fonts/daimeng.ttf') format('truetype'); /* 呆萌手写体 */
  font-display: swap;
}
@font-face {
  font-family: 'Jiangcheng';
  src: url('@/assets/fonts/jiangcheng.ttf') format('truetype'); /* 江城圆体 */
  font-display: swap;
}

:root {
  /* 明亮主题变量 */
  --primary: #F4A261;
  --secondary: #E9C46A;
  --accent: #76B5C5;
  --bg-color: #FFFBF5;
  --text-main: #5D4037;
  --card-bg: rgba(255, 255, 255, 0.8);
}

[data-theme='dark'] {
  /* 深色主题变量 */
  --primary: #E76F51;
  --secondary: #D4A373;
  --accent: #457B9D;
  --bg-color: #1B262C;
  --text-main: #E0E0E0;
  --card-bg: rgba(33, 47, 60, 0.8);
}

body {
  margin: 0;
  background-color: var(--bg-color);
  color: var(--text-main);
  font-family: 'Jiangcheng', sans-serif;
  transition: background-color 0.5s ease;
}

/* 统一可爱的滚动条 */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: var(--secondary); border-radius: 10px; }
</style>
