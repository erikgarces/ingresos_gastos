# api/serializers.py
from rest_framework import serializers
from traker.models import Transaction, Category, Project


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'color', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        # Automáticamente asignar el usuario actual
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        # Automáticamente asignar el usuario actual
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'type', 'amount', 'description', 'date', 
            'category', 'category_name', 'project', 'project_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'category_name', 'project_name']

    def create(self, validated_data):
        # Automáticamente asignar el usuario actual
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_category(self, value):
        """Validar que la categoría pertenezca al usuario actual"""
        if value.user != self.context['request'].user:
            raise serializers.ValidationError("No tienes permiso para usar esta categoría.")
        return value

    def validate_project(self, value):
        """Validar que el proyecto pertenezca al usuario actual"""
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("No tienes permiso para usar este proyecto.")
        return value