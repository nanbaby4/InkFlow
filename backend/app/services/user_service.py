from databases import Database
from sqlalchemy import and_, func, select

from app.exceptions import BusinessException, ErrorCode, throw_if, throw_if_not
from app.models.user import User
from app.schemas.user import (
    LoginUserVO, UserAddRequest, UserLoginRequest, UserQueryRequest,
    UserRegisterRequest, UserUpdateRequest, UserVO
)
from app.utils.password import encrypt_password


class UserService:
    """用户服务"""

    def __init__(self, db: Database):
        self.db = db

    async def register(self, request: UserRegisterRequest) -> int:
        """用户注册"""
        throw_if(
            len(request.user_account) < 4,
            ErrorCode.PARAMS_ERROR,
            "账号长度不能小于 4 位"
        )
        throw_if(
            len(request.user_password) < 8,
            ErrorCode.PARAMS_ERROR,
            "密码长度不能小于 8 位"
        )
        throw_if(
            request.user_password != request.check_password,
            ErrorCode.PARAMS_ERROR,
            "两次输入的密码不一致"
        )

        query = select(func.count(User.id)).where(
            and_(User.user_account == request.user_account, User.is_delete == 0)
        )
        count = await self.db.fetch_val(query)
        throw_if(count > 0, ErrorCode.USER_ALREADY_EXIST, "账号已存在")

        encrypted_password = encrypt_password(request.user_password)

        query = """
            INSERT INTO user (userAccount, userPassword, userName, userRole)
            VALUES (:userAccount, :userPassword, :userName, :userRole)
        """
        user_id = await self.db.execute(
            query=query,
            values={
                "userAccount": request.user_account,
                "userPassword": encrypted_password,
                "userName": f"用户{request.user_account}",
                "userRole": "user"
            }
        )

        return user_id

    async def login(self, request: UserLoginRequest) -> LoginUserVO:
        """用户登录"""
        throw_if(
            len(request.user_account) < 4,
            ErrorCode.PARAMS_ERROR,
            "账号长度不能小于 4 位"
        )
        throw_if(
            len(request.user_password) < 8,
            ErrorCode.PARAMS_ERROR,
            "密码长度不能小于 8 位"
        )

        query = select(User).where(
            and_(User.user_account == request.user_account, User.is_delete == 0)
        )
        user = await self.db.fetch_one(query)
        throw_if_not(user, ErrorCode.USER_NOT_EXIST, "用户不存在")

        encrypted_password = encrypt_password(request.user_password)
        throw_if(
            user["userPassword"] != encrypted_password,
            ErrorCode.PASSWORD_ERROR,
            "密码错误"
        )

        return LoginUserVO(
            id=user["id"],
            userAccount=user["userAccount"],
            userName=user["userName"],
            userAvatar=user["userAvatar"],
            userProfile=user["userProfile"],
            userRole=user["userRole"],
            createTime=user["createTime"].isoformat(),
            updateTime=user["updateTime"].isoformat()
        )
    

    async def get_user_by_id(self, user_id: int):
        query = select(User).where(
                and_(User.id == user_id, User.is_delete == 0)
            )
        user_record = await self.db.fetch_one(query=query)

        if not user_record:
            raise BusinessException(ErrorCode.NOT_FOUND_ERROR, "用户不存在")
        return LoginUserVO(**dict(user_record))

    async def list_by_page(self, request: UserQueryRequest):
        """分页查询用户列表"""
        conditions = [User.is_delete == 0]

        if request.id is not None:
            conditions.append(User.id == request.id)
        if request.user_account:
            conditions.append(User.user_account.like(f"%{request.user_account}%"))
        if request.user_name:
            conditions.append(User.user_name.like(f"%{request.user_name}%"))
        if request.user_profile:
            conditions.append(User.user_profile.like(f"%{request.user_profile}%"))
        if request.user_role:
            conditions.append(User.user_role == request.user_role)

        # 统计总数
        count_query = select(func.count(User.id)).where(and_(*conditions))
        total = await self.db.fetch_val(count_query)

        # 分页查询
        query = select(User).where(and_(*conditions))

        # 排序
        if request.sort_field and hasattr(User, request.sort_field):
            sort_column = getattr(User, request.sort_field)
            if request.sort_order == "ascend":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(User.create_time.desc())

        offset = (request.current - 1) * request.page_size
        query = query.offset(offset).limit(request.page_size)

        rows = await self.db.fetch_all(query)
        users = [UserVO(**dict(row)) for row in rows]

        return users, total

    async def add_user(self, request: UserAddRequest) -> int:
        """添加用户（管理员）"""
        throw_if(
            len(request.user_account) < 4,
            ErrorCode.PARAMS_ERROR,
            "账号长度不能小于 4 位"
        )
        throw_if(
            len(request.user_password) < 8,
            ErrorCode.PARAMS_ERROR,
            "密码长度不能小于 8 位"
        )

        # 检查账号是否已存在
        query = select(func.count(User.id)).where(
            and_(User.user_account == request.user_account, User.is_delete == 0)
        )
        count = await self.db.fetch_val(query)
        throw_if(count > 0, ErrorCode.USER_ALREADY_EXIST, "账号已存在")

        encrypted_password = encrypt_password(request.user_password)

        query = """
            INSERT INTO user (userAccount, userPassword, userName, userAvatar, userProfile, userRole)
            VALUES (:userAccount, :userPassword, :userName, :userAvatar, :userProfile, :userRole)
        """
        user_id = await self.db.execute(
            query=query,
            values={
                "userAccount": request.user_account,
                "userPassword": encrypted_password,
                "userName": request.user_name or f"用户{request.user_account}",
                "userAvatar": request.user_avatar or "",
                "userProfile": request.user_profile or "",
                "userRole": request.user_role
            }
        )

        return user_id

    async def update_user(self, request: UserUpdateRequest) -> bool:
        """更新用户（管理员）"""
        query = select(User).where(
            and_(User.id == request.id, User.is_delete == 0)
        )
        user = await self.db.fetch_one(query)
        throw_if_not(user, ErrorCode.USER_NOT_EXIST, "用户不存在")

        update_sql = "UPDATE user SET updateTime = NOW()"
        values = {}

        if request.user_name is not None:
            update_sql += ", userName = :userName"
            values["userName"] = request.user_name
        if request.user_avatar is not None:
            update_sql += ", userAvatar = :userAvatar"
            values["userAvatar"] = request.user_avatar
        if request.user_profile is not None:
            update_sql += ", userProfile = :userProfile"
            values["userProfile"] = request.user_profile
        if request.user_role is not None:
            update_sql += ", userRole = :userRole"
            values["userRole"] = request.user_role

        update_sql += " WHERE id = :id"
        values["id"] = request.id

        await self.db.execute(query=update_sql, values=values)
        return True

    async def delete_user(self, user_id: int) -> bool:
        """删除用户（管理员，软删除）"""
        query = select(User).where(
            and_(User.id == user_id, User.is_delete == 0)
        )
        user = await self.db.fetch_one(query)
        throw_if_not(user, ErrorCode.USER_NOT_EXIST, "用户不存在")

        query = "UPDATE user SET isDelete = 1 WHERE id = :id"
        await self.db.execute(query=query, values={"id": user_id})
        return True
