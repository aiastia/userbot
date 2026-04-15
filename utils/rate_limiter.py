"""限速器 - 控制消息转发频率"""
import time
import asyncio
import logging
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    令牌桶 + 滑动窗口限速器
    用于控制转发频率，避免被 Telegram 限制
    """

    def __init__(self, max_per_minute=5, max_per_hour=30, min_interval=3):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.min_interval = min_interval

        # 滑动窗口记录时间戳
        self._minute_window = deque()
        self._hour_window = deque()
        self._last_action_time = 0

        # 锁，防止并发问题
        self._lock = asyncio.Lock()

    async def acquire(self):
        """
        获取执行许可，如果超过限速则等待
        返回 True 表示获得许可
        """
        async with self._lock:
            now = time.time()

            # 清理过期时间戳
            self._cleanup_old(now)

            # 检查最小间隔
            if now - self._last_action_time < self.min_interval:
                wait_time = self.min_interval - (now - self._last_action_time)
                logger.debug(f"限速等待: {wait_time:.1f}秒")
                await asyncio.sleep(wait_time)
                now = time.time()

            # 检查每分钟限制
            if len(self._minute_window) >= self.max_per_minute:
                oldest = self._minute_window[0]
                wait_time = 60 - (now - oldest) + 0.1
                if wait_time > 0:
                    logger.warning(f"达到每分钟限制({self.max_per_minute}/min)，等待 {wait_time:.1f}秒")
                    await asyncio.sleep(wait_time)
                    now = time.time()
                    self._cleanup_old(now)

            # 检查每小时限制
            if len(self._hour_window) >= self.max_per_hour:
                oldest = self._hour_window[0]
                wait_time = 3600 - (now - oldest) + 0.1
                if wait_time > 0:
                    logger.warning(f"达到每小时限制({self.max_per_hour}/h)，等待 {wait_time:.1f}秒")
                    await asyncio.sleep(wait_time)
                    now = time.time()
                    self._cleanup_old(now)

            # 记录本次操作时间
            self._minute_window.append(now)
            self._hour_window.append(now)
            self._last_action_time = now

            return True

    def _cleanup_old(self, now):
        """清理过期的滑动窗口记录"""
        # 清理超过1分钟的记录
        while self._minute_window and now - self._minute_window[0] > 60:
            self._minute_window.popleft()

        # 清理超过1小时的记录
        while self._hour_window and now - self._hour_window[0] > 3600:
            self._hour_window.popleft()

    @property
    def status(self):
        """返回当前限速状态"""
        now = time.time()
        self._cleanup_old(now)
        return {
            "minute_used": len(self._minute_window),
            "minute_limit": self.max_per_minute,
            "hour_used": len(self._hour_window),
            "hour_limit": self.max_per_hour,
        }