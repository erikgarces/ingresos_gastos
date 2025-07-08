from rest_framework import viewsets, filters # , status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count #, Q
from django.utils import timezone
from datetime import datetime #, timedelta

from traker.serializers import CategorySerializer, ProjectSerializer, TransactionSerializer # UserSerializer,
from traker.models import Category, Project, Transaction


class BaseUserViewSet(viewsets.ModelViewSet):
    """ViewSet base que filtra por usuario automáticamente"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar queryset por usuario actual"""
        return self.queryset.filter(user=self.request.user)


class CategoryViewSet(BaseUserViewSet):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Obtener todas las transacciones de una categoría"""
        category = self.get_object()
        transactions = Transaction.objects.filter(
            category=category,
            user=request.user
        )
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Resumen de transacciones por categoría"""
        category = self.get_object()
        transactions = Transaction.objects.filter(
            category=category,
            user=request.user
        )
        
        total_income = transactions.filter(type_transaction='income').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_expense = transactions.filter(type_transaction='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        transaction_count = transactions.count()
        
        return Response({
            'category': category.name,
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'transaction_count': transaction_count
        })


class ProjectViewSet(BaseUserViewSet):

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Obtener todas las transacciones de un proyecto"""
        project = self.get_object()
        transactions = Transaction.objects.filter(
            project=project,
            user=request.user
        )
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Resumen de transacciones por proyecto"""
        project = self.get_object()
        transactions = Transaction.objects.filter(
            project=project,
            user=request.user
        )
        
        total_income = transactions.filter(type='income').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_expense = transactions.filter(type='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Resumen por categoría dentro del proyecto
        category_summary = transactions.values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('category__name')
        
        return Response({
            'project': project.name,
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'transaction_count': transactions.count(),
            'category_breakdown': category_summary
        })

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activar/desactivar proyecto"""
        project = self.get_object()
        project.is_active = not project.is_active
        project.save()
        return Response({
            'message': f'Proyecto {"activado" if project.is_active else "desactivado"}',
            'is_active': project.is_active
        })


class TransactionViewSet(BaseUserViewSet):

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'category', 'project', 'date']
    search_fields = ['description']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date', '-created_at']

    def get_queryset(self):
        """Filtrar queryset por usuario y parámetros adicionales"""
        queryset = super().get_queryset()
        
        # Filtros adicionales por query params
        transaction_type = self.request.query_params.get('type_transaction', None)
        category_id = self.request.query_params.get('category', None)
        project_id = self.request.query_params.get('project', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        amount_min = self.request.query_params.get('amount_min', None)
        amount_max = self.request.query_params.get('amount_max', None)
        
        if transaction_type:
            queryset = queryset.filter(type_transaction=transaction_type)
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=date_from)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=date_to)
            except ValueError:
                pass
        
        if amount_min:
            try:
                queryset = queryset.filter(amount__gte=float(amount_min))
            except ValueError:
                pass
        
        if amount_max:
            try:
                queryset = queryset.filter(amount__lte=float(amount_max))
            except ValueError:
                pass
        
        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Resumen general de transacciones del usuario"""
        queryset = self.get_queryset()
        
        total_income = queryset.filter(type_transaction='income').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_expense = queryset.filter(type_transaction='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Resumen por categoría
        category_summary = queryset.values('category__name', 'type_transaction').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('category__name')
        
        # Resumen por proyecto
        project_summary = queryset.filter(project__isnull=False).values(
            'project__name', 'type'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('project__name')
        
        # Transacciones recientes
        recent_transactions = TransactionSerializer(
            queryset[:10], 
            many=True, 
            context={'request': request}
        ).data
        
        return Response({
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'transaction_count': queryset.count(),
            'category_breakdown': category_summary,
            'project_breakdown': project_summary,
            'recent_transactions': recent_transactions
        })

    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        """Resumen mensual de transacciones"""
        year = request.query_params.get('year', timezone.now().year)
        
        try:
            year = int(year)
        except ValueError:
            year = timezone.now().year
        
        queryset = self.get_queryset().filter(date__year=year)
        
        # Resumen por mes
        monthly_data = []
        for month in range(1, 13):
            month_transactions = queryset.filter(date__month=month)
            income = month_transactions.filter(type_transaction='income').aggregate(
                total=Sum('amount')
            )['total'] or 0
            expense = month_transactions.filter(type_transaction='expense').aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            monthly_data.append({
                'month': month,
                'income': income,
                'expense': expense,
                'balance': income - expense,
                'transaction_count': month_transactions.count()
            })
        
        return Response({
            'year': year,
            'monthly_data': monthly_data
        })

    @action(detail=False, methods=['get'])
    def export_data(self, request):
        """Exportar datos para análisis externo"""
        queryset = self.get_queryset()
        
        # Preparar datos para exportar
        export_data = []
        for transaction in queryset:
            export_data.append({
                'id': transaction.id,
                'type': transaction.type,
                'amount': float(transaction.amount),
                'description': transaction.description,
                'date': transaction.date.strftime('%Y-%m-%d'),
                'category': transaction.category.name,
                'project': transaction.project.name if transaction.project else None,
                'created_at': transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return Response({
            'count': len(export_data),
            'transactions': export_data
        })