import uuid

from fastapi import APIRouter, Depends, Request, Response
from databases import Database

from app.database import get_db
from app.deps import require_admin
from app.exceptions import BusinessException, ErrorCode
from app.schemas.common import BaseResponse, DeleteRequest
from app.schemas.user import LoginUserVO, UserAddRequest, UserLoginRequest, UserQueryRequest, UserRegisterRequest, UserUpdateRequest, UserVO
from app.services.user_service import UserService
from app.utils.auth import SESSION_COOKIE_KEY
from app.utils.session import get_session, set_session, remove_session

router = APIRouter(prefix="/user", tags=["userManage"])


@router.post("/register", response_model=BaseResponse[int])
async def register(request: UserRegisterRequest, db: Database = Depends(get_db)):
    """用户注册"""
    service = UserService(db)
    user_id = await service.register(request)
    return BaseResponse.success(data=user_id, message="注册成功")


@router.post("/login", response_model=BaseResponse[LoginUserVO])
async def login(
    request: UserLoginRequest,
    response: Response,
    db: Database = Depends(get_db),
):
    """用户登录"""
    service = UserService(db)
    login_user = await service.login(request)

    session_id = uuid.uuid4().hex
    await set_session(session_id, login_user.model_dump(by_alias=True, mode="json"))

    response.set_cookie(
        key=SESSION_COOKIE_KEY,
        value=session_id,
        max_age=2592000,  # 30 天
        httponly=True,
        samesite="lax",
    )

    return BaseResponse.success(data=login_user, message="登录成功")


@router.get("/getLoginUser", response_model=BaseResponse[LoginUserVO])
async def get_login_user(request: Request, db: Database = Depends(get_db)):
    """获取当前登录用户信息"""
    session_id = request.cookies.get(SESSION_COOKIE_KEY)
    if not session_id:
        raise BusinessException(ErrorCode.NOT_LOGIN_ERROR)
    user_data = await get_session(session_id)
    if not user_data:
        raise BusinessException(ErrorCode.NOT_LOGIN_ERROR)
    service = UserService(db)
    login_user_vo = await service.get_user_by_id(user_data["id"])
    return BaseResponse.success(data=login_user_vo)


@router.post("/logout", response_model=BaseResponse[bool])
async def logout(request: Request, response: Response):
    """用户登出"""
    session_id = request.cookies.get(SESSION_COOKIE_KEY)
    if session_id:
        await remove_session(session_id)
    response.delete_cookie(SESSION_COOKIE_KEY)
    return BaseResponse.success(data=True, message="登出成功")


@router.get("/get", response_model=BaseResponse[UserVO])
async def get_user_by_id(
    id: int,
    db: Database = Depends(get_db)
):
    """根据 ID 获取用户"""
    service = UserService(db)
    user = await service.get_user_by_id(id)
    return BaseResponse.success(data=user)


@router.post("/list/page", response_model=BaseResponse[dict])
async def list_users_by_page(
    request: UserQueryRequest,
    db: Database = Depends(get_db),
    _: LoginUserVO = Depends(require_admin)
):
    """分页查询用户列表（管理员）"""
    service = UserService(db)
    users, total = await service.list_by_page(request)
    
    return BaseResponse.success(data={
        "records": users,
        "total": total,
        "current": request.current,
        "size": request.page_size
    })


@router.post("/add", response_model=BaseResponse[int])
async def add_user(
    request: UserAddRequest,
    db: Database = Depends(get_db),
    _: LoginUserVO = Depends(require_admin)
):
    """添加用户（管理员）"""
    service = UserService(db)
    user_id = await service.add_user(request)
    return BaseResponse.success(data=user_id, message="添加成功")


@router.post("/update", response_model=BaseResponse[bool])
async def update_user(
    request: UserUpdateRequest,
    db: Database = Depends(get_db),
    _: LoginUserVO = Depends(require_admin)
):
    """更新用户（管理员）"""
    service = UserService(db)
    result = await service.update_user(request)
    return BaseResponse.success(data=result, message="更新成功")


@router.post("/delete", response_model=BaseResponse[bool])
async def delete_user(
    request: DeleteRequest,
    db: Database = Depends(get_db),
    _: LoginUserVO = Depends(require_admin)
):
    """删除用户（管理员）"""
    service = UserService(db)
    result = await service.delete_user(request.id)
    return BaseResponse.success(data=result, message="删除成功")
