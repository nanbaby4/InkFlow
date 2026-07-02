<template>
  <div class="header-wrapper">
    <a-row align="middle" class="header-content">
      <a-col flex="200px" class="logo-area" @click="router.push('/')">
        <img src="@/assets/logo.png" class="logo-icon" />
        <span class="logo-text">灵感墨水</span>
      </a-col>

      <a-col flex="auto">
        <a-menu v-model:selectedKeys="selectedKeys" mode="horizontal" class="cute-menu" @click="handleNavClick">
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

        <a-button type="primary" class="magic-btn" @click="router.push('/create')">
          ✨ 帮我写个爆款
        </a-button>

        <!-- 未登录：显示登录按钮 -->
        <a-button v-if="!userStore.loginUser.id" type="text" class="login-btn" @click="router.push('/user/login')">
          🔑 登录
        </a-button>

        <!-- 已登录：显示用户头像 + 悬浮下拉 -->
        <a-dropdown v-else trigger="hover">
          <a-avatar
            :src="userStore.loginUser.userAvatar || `https://api.dicebear.com/7.x/adventurer/svg?seed=${userStore.loginUser.userName || 'Felix'}`"
            :size="40"
            class="user-avatar"
          />
          <template #overlay>
            <a-menu @click="handleMenuClick">
              <a-menu-item key="profile">
                <span>👤 个人中心</span>
              </a-menu-item>
              <a-menu-divider />
              <a-menu-item key="logout">
                <span style="color: #e74c3c">🚪 退出登录</span>
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { message } from 'ant-design-vue';
import { useUserStore } from '@/stores/user.js';

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const selectedKeys = ref(['/']);
const isDark = ref(false);

onMounted(async () => {
  isDark.value = localStorage.getItem('theme') === 'dark';
  // 主动获取登录用户信息，不依赖路由守卫的调用时机
  await userStore.fetchLoginUser();
});

// 同步菜单高亮到当前路由
watch(
  () => route.path,
  (path) => {
    if (path === '/') selectedKeys.value = ['/']
    else if (path.startsWith('/create')) selectedKeys.value = ['/create']
    else if (path.startsWith('/gallery')) selectedKeys.value = ['/gallery']
  },
  { immediate: true },
)

const toggleTheme = () => {
  isDark.value = !isDark.value;
  const newTheme = isDark.value ? 'dark' : 'light';
  window.dispatchEvent(new CustomEvent('theme-change', { detail: newTheme }));
};

const handleNavClick = ({ key }) => {
  router.push(key)
};

const handleMenuClick = async ({ key }) => {
  if (key === 'logout') {
    await userStore.logout();
    message.success('👋 已退出，期待下次灵感碰撞！');
    router.push('/');
  } else if (key === 'profile') {
    // TODO: 跳转个人中心页
    message.info('个人中心开发中...');
  }
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
