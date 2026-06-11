from fastapi import Request, Depends
from app.exceptions import BusinessException, ErrorCode
from app.utils.session import get_session

SESSION_COOKIE_KEY = "session_id"

async def get_login_user(request: Request):
    """
    这是一个依赖项：从 Cookie 拿到 SessionID，去 Redis 查用户
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise BusinessException(ErrorCode.NOT_LOGIN_ERROR) # 抛出 40100 错误
    
    user_data = await get_session(session_id)
    if not user_data:
        raise BusinessException(ErrorCode.NOT_LOGIN_ERROR)
        
    return user_data # 返回用户信息字典