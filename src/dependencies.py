from src.routers.auth import fastapi_users

# Current active user dependency
current_active_user = fastapi_users.current_user(active=True)
current_user = fastapi_users.current_user()
