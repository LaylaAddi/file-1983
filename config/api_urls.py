from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # JWT token endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Auth endpoints (stubbed — implemented in Step 2)
    # path('auth/register/', ...),
    # path('auth/login/', ...),

    # Document endpoints (stubbed — implemented in Step 4+)
    # path('documents/', ...),
]
