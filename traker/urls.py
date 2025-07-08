from django.urls import path, include
from rest_framework.routers import DefaultRouter
from traker.views import CategoryViewSet, ProjectViewSet, TransactionViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'transactions', TransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # path('auth/', include('rest_framework.urls')),  # Para autenticación en DRF
]