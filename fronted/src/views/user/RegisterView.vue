<template>
  <div id="userRegisterView">
    <div class="login-container">
      <a-row class="login-card">
        <!-- 右侧：表单区（这里我们调换一下位置，增加变化） -->
        <a-col :xs="24" :md="12" class="login-form-area">
          <div class="form-wrapper">
            <h1 class="form-title">🌱 种下灵感新芽</h1>
            <a-form :model="formState" layout="vertical" @finish="onFinish">
              <a-form-item label="账号名称" name="userAccount" :rules="[{ required: true, min: 4 }]">
                <a-input v-model:value="formState.userAccount" placeholder="想一个酷炫的名字" />
              </a-form-item>

              <a-form-item label="设置密码" name="userPassword" :rules="[{ required: true, min: 8 }]">
                <a-input-password v-model:value="formState.userPassword" placeholder="至少8位神秘字符" />
              </a-form-item>

              <a-form-item label="确认密码" name="checkPassword" :rules="[{ required: true }]">
                <a-input-password v-model:value="formState.checkPassword" placeholder="再次确认密码" />
              </a-form-item>

              <a-button type="primary" html-type="submit" :loading="loading" block class="magic-btn register-btn">
                🎨 准备好了，去创作！
              </a-button>

              <div class="switch-link">
                已经有账号了？<router-link to="/user/login">✨ 直接召唤登录</router-link>
              </div>
            </a-form>
          </div>
        </a-col>

        <!-- 左侧：插画区 -->
        <a-col :xs="0" :md="12" class="login-illustration accent-bg">
          <div class="illustration-content">
            <div class="sprout-icon">🌱</div>
            <h2 class="handwritten">开启你的爆款之路</h2>
            <p>在这里，每一行文字都能开出花来。</p>
          </div>
        </a-col>
      </a-row>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { message } from 'ant-design-vue';
import { useRouter } from 'vue-router';
import myAxios from '@/request';

const router = useRouter();
const loading = ref(false);

const formState = reactive({
  userAccount: '',
  userPassword: '',
  checkPassword: '',
});

const onFinish = async (values) => {
  if (values.userPassword !== values.checkPassword) {
    message.error('两次输入的密码不一致哦');
    return;
  }
  loading.value = true;
  try {
    const res = await myAxios.post('/user/register', values);
    if (res.data.code === 0) {
      message.success('🌱 新芽种好了！快去登录吧');
      router.push('/user/login');
    } else {
      message.error(res.data.message);
    }
  } catch (error) {
    message.error('网络开小差了');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
/* 继承大部分 Login 的样式，修改颜色 */
#userRegisterView {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0f7ff 0%, #fffbf5 100%);
}

.accent-bg {
  background: var(--accent) !important;
  color: white !important;
}

.sprout-icon {
  font-size: 80px;
  animation: bounce 2s infinite ease-in-out;
}

.register-btn {
  background: var(--accent);
  box-shadow: 0 10px 20px rgba(118, 181, 197, 0.3);
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px) scale(1.1); }
}

/* 统一卡片样式 */
.login-container { width: 100%; max-width: 900px; padding: 20px; }
.login-card { background: var(--card-bg); border-radius: 40px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.05); border: 4px solid #fff; }
.login-illustration { display: flex; align-items: center; justify-content: center; text-align: center; padding: 40px; }
.login-form-area { padding: 60px 40px; }
.form-title { font-family: 'Daimeng', cursive; margin-bottom: 40px; font-size: 32px; color: var(--accent); }
.magic-btn { height: 50px; font-size: 18px; font-weight: bold; border-radius: 20px; margin-top: 20px; transition: all 0.3s; color: white; border: none; }
.switch-link { margin-top: 20px; text-align: center; font-size: 14px; }
.handwritten { font-family: 'Daimeng', cursive; margin-top: 20px; font-size: 28px; }
</style>
