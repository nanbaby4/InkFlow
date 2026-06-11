<template>
  <div class="header-wrapper">
    <a-row align="middle" class="header-content">
      <a-col flex="200px" class="logo-area" @click="router.push('/')">
        <img src="@/assets/logo.png" class="logo-icon" />
        <span class="logo-text">灵感墨水</span>
      </a-col>

      <a-col flex="auto">
        <a-menu v-model:selectedKeys="selectedKeys" mode="horizontal" class="cute-menu">
          <a-menu-item key="/">🏠 灵感森林</a-menu-item>
          <a-menu-item key="/create">🎨 创作实验室</a-menu-item>
          <a-menu-item key="/gallery">🌈 墨迹画廊</a-menu-item>
        </a-menu>
      </a-col>

      <a-col flex="260px" class="right-area">
        <!-- 果冻换肤按钮 -->
        <div class="theme-toggle" @click="toggleTheme">
          <div class="toggle-ball" :class="{ 'is-dark': isDark }">
            {{ isDark ? '🌙' : '☀️' }}
          </div>
        </div>

        <a-button type="primary" class="magic-btn">
          ✨ 帮我写个爆款
        </a-button>

        <!-- 未登录：显示登录按钮 -->
        <a-button v-if="!userStore.loginUser.id" type="text" class="login-btn" @click="router.push('/user/login')">
          🔑 登录
        </a-button>

        <!-- 已登录：显示用户头像 -->
        <a-avatar
          v-else
          :src="userStore.loginUser.avatar || `https://api.dicebear.com/7.x/adventurer/svg?seed=${userStore.loginUser.userName || 'Felix'}`"
          :size="40"
          class="user-avatar"
        />
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user.js';

const router = useRouter();
const userStore = useUserStore();
const selectedKeys = ref(['/']);
const isDark = ref(false);

onMounted(() => {
  isDark.value = localStorage.getItem('theme') === 'dark';
});

const toggleTheme = () => {
  isDark.value = !isDark.value;
  const newTheme = isDark.value ? 'dark' : 'light';
  window.dispatchEvent(new CustomEvent('theme-change', { detail: newTheme }));
};
</script>

<style scoped>
.header-wrapper {
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  padding: 0 40px;
  border-radius: 0 0 30px 30px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo-area {
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: transform 0.3s;
}
.logo-area:hover { transform: scale(1.05) rotate(-2deg); }
.logo-icon { height: 40px; }
.logo-text {
  font-family: 'Daimeng';
  font-size: 24px;
  color: var(--primary);
  margin-left: 10px;
}

.cute-menu {
  background: transparent;
  border-bottom: none;
  font-size: 16px;
}

.right-area {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 15px;
}

/* 换肤开关 */
.theme-toggle {
  width: 54px;
  height: 28px;
  background: var(--secondary);
  border-radius: 20px;
  padding: 3px;
  cursor: pointer;
  box-shadow: inset 0 2px 5px rgba(0,0,0,0.1);
}
.toggle-ball {
  width: 22px;
  height: 22px;
  background: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}
.is-dark { transform: translateX(26px); background: #1B262C; }

.magic-btn {
  border-radius: 15px;
  font-weight: bold;
  height: 40px;
  box-shadow: 0 4px 15px var(--primary);
}
.magic-btn:active { transform: scale(0.95); }

.login-btn {
  font-size: 16px;
  font-weight: bold;
  color: var(--primary);
  border-radius: 12px;
  transition: all 0.3s;
}
.login-btn:hover {
  background: var(--secondary);
  transform: scale(1.05);
}

.user-avatar { border: 3px solid var(--secondary); cursor: pointer; }
</style>
