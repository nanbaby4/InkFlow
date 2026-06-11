<template>
  <div class="footer-wrapper">
    <div class="ink-sprout">🌱</div>
    <p class="slogan">让每一刻灵感，都变成美丽的墨迹</p>
    <div class="footer-links">
      <a href="#">🌟 创作指南</a>
      <span class="divider">|</span>
      <a href="#">🎨 墨水精灵</a>
      <span class="divider">|</span>
      <a href="#">📈 热门趋势</a>
    </div>
    <div class="copyright">
      © 2026 InkFlow ·召唤灵感中 · nan_n
    </div>
  </div>
</template>

<style scoped>
.footer-wrapper {
  padding: 60px 20px;
  text-align: center;
  position: relative;
}

.ink-sprout {
  font-size: 30px;
  margin-bottom: 10px;
  animation: sprout-wiggle 3s infinite ease-in-out;
}

@keyframes sprout-wiggle {
  0%, 100% { transform: rotate(0); }
  50% { transform: rotate(15deg) scale(1.1); }
}

.slogan {
  font-family: 'Daimeng';
  font-size: 20px;
  color: var(--primary);
  margin-bottom: 20px;
}

.footer-links {
  margin-bottom: 15px;
}
.footer-links a {
  color: var(--text-main);
  opacity: 0.7;
}
.footer-links a:hover {
  opacity: 1;
  color: var(--accent);
}
.divider { margin: 0 15px; color: var(--secondary); }

.copyright {
  font-size: 12px;
  opacity: 0.5;
  letter-spacing: 1px;
}
</style>
