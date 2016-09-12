from rest_framework.authentication import SessionAuthentication
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin
from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.viewsets import GenericViewSet
from hsreplaynet.api.authentication import AuthTokenAuthentication, RequireAuthToken
from hsreplaynet.api.permissions import IsOwnerOrStaff, APIKeyPermission
from hsreplaynet.api.serializers import UserSerializer
from .models import Pack


class PackSerializer(HyperlinkedModelSerializer):
	user = UserSerializer()

	class Meta:
		model = Pack
		fields = ("user", "booster_type", "date")


class PackViewSet(CreateModelMixin, RetrieveModelMixin, GenericViewSet):
	authentication_classes = (SessionAuthentication, AuthTokenAuthentication)
	permission_classes = (IsOwnerOrStaff, RequireAuthToken, APIKeyPermission)
	queryset = Pack.objects.all()
	serializer_class = PackSerializer
