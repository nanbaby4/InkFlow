<template>
  <div id="userLoginView">
    <div class="login-container">
      <a-row class="login-card">
        <!-- 左侧：治愈系插画区 -->
        <a-col :xs="0" :md="12" class="login-illustration">
          <div class="illustration-content">
            <div class="ink-monster">🐙</div>
            <h2 class="handwritten">欢迎回来，灵感家！</h2>
            <p>每一滴墨水，都在期待你的召唤...</p>
          </div>
        </a-col>

        <!-- 右侧：表单区 -->
        <a-col :xs="24" :md="12" class="login-form-area">
          <div class="form-wrapper">
            <h1 class="form-title">✨ 召唤登录</h1>
            <a-form :model="formState" layout="vertical" @finish="onFinish">
              <a-form-item
                label="账号"
                name="userAccount"
                :rules="[{ required: true, message: '请输入你的灵感账号' }]"
              >
                <a-input v-model:value="formState.userAccount" placeholder="你的账号名称" size="large" />
              </a-form-item>

              <a-form-item
                label="密码"
                name="userPassword"
                :rules="[{ required: true, message: '请输入神秘密码' }]"
              >
                <a-input-password v-model:value="formState.userPassword" placeholder="嘘，在这里输入密码" size="large" />
              </a-form-item>

              <div class="form-actions">
                <a-button type="primary" html-type="submit" :loading="loading" block class="magic-btn">
                  🚀 开启创作旅程
                </a-button>
                <div class="switch-link">
                  还没有账号？<router-link to="/user/register">🌱 种下一颗新芽</router-link>
                </div>
              </div>
            </a-form>
          </div>
        </a-col>
      </a-row>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { message } from 'ant-design-vue';
import { useRouter, useRoute } from 'vue-router';
import { userLogin } from '@/api/userManage.js'

const router = useRouter();
const route = useRoute();
const loading = ref(false);

const formState = reactive({
  userAccount: '',
  userPassword: '',
});

const onFinish = async (values) => {
  loading.value = true;
  try {
    const res = await userLogin(values);
    if (res.data.code === 0) {
      message.success('🌈 登录成功！欢迎回来');
      // 处理重定向
      const redirect = route.query?.redirect ?? '/';
      window.location.href = redirect;
    } else {
      message.error('❌ ' + res.data.message);
    }
  } catch (error) {
    message.error('召唤失败，请检查网络');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
#userLoginView {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fff5f0 0%, #fffbf5 100%);
}

.login-container {
  width: 100%;
  max-width: 900px;
  padding: 20px;
}

.login-card {
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  border-radius: 40px;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(244, 162, 97, 0.15);
  border: 4px solid #fff;
}

.login-illustration {
  background: var(--secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px;
  color: #5d4037;
}

.ink-monster {
  font-size: 80px;
  animation: wiggle 3s infinite ease-in-out;
}

.handwritten {
  font-family: 'Daimeng', cursive;
  margin-top: 20px;
  font-size: 28px;
}

.login-form-area {
  padding: 60px 40px;
}

.form-title {
  font-family: 'Daimeng', cursive;
  color: var(--primary);
  margin-bottom: 40px;
  font-size: 32px;
}

.magic-btn {
  height: 50px;
  font-size: 18px;
  font-weight: bold;
  border-radius: 20px;
  margin-top: 20px;
  box-shadow: 0 10px 20px rgba(244, 162, 97, 0.3);
}

.magic-btn:active {
  transform: scale(0.96);
}

.switch-link {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
}

@keyframes wiggle {
  0%, 100% { transform: rotate(-5deg) scale(1); }
  50% { transform: rotate(5deg) scale(1.1); }
}

:deep(.ant-input-affix-wrapper), :deep(.ant-input) {
  border-radius: 12px;
}
</style>
