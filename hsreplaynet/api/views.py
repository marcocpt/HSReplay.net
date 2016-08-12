from rest_framework.authentication import SessionAuthentication
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, RetrieveModelMixin
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveDestroyAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.status import HTTP_201_CREATED
from hsreplaynet.accounts.models import AccountClaim
from hsreplaynet.games.models import GameReplay
from hsreplaynet.uploads.models import UploadEvent
from . import serializers
from .authentication import AuthTokenAuthentication, RequireAuthToken
from .models import AuthToken, APIKey
from .permissions import APIKeyPermission, IsOwnerOrReadOnly


class WriteOnlyOnceViewSet(
	CreateModelMixin, UpdateModelMixin, RetrieveModelMixin, GenericViewSet
):
	pass


class AuthTokenViewSet(WriteOnlyOnceViewSet):
	permission_classes = (APIKeyPermission, )
	queryset = AuthToken.objects.all()
	serializer_class = serializers.AuthTokenSerializer


class APIKeyViewSet(WriteOnlyOnceViewSet):
	permission_classes = (AllowAny, )
	queryset = APIKey.objects.all()
	serializer_class = serializers.APIKeySerializer


class CreateAccountClaimView(CreateAPIView):
	authentication_classes = (AuthTokenAuthentication, )
	permission_classes = (RequireAuthToken, )
	queryset = AccountClaim.objects.all()
	serializer_class = serializers.AccountClaimSerializer

	def create(self, request):
		claim, _ = AccountClaim.objects.get_or_create(token=request.auth_token)
		serializer = self.get_serializer(claim)
		headers = self.get_success_headers(serializer.data)
		response = Response(serializer.data, status=HTTP_201_CREATED, headers=headers)
		return response


class UploadEventViewSet(WriteOnlyOnceViewSet):
	authentication_classes = (AuthTokenAuthentication, SessionAuthentication)
	permission_classes = (RequireAuthToken, APIKeyPermission)
	queryset = UploadEvent.objects.all()
	serializer_class = serializers.UploadEventSerializer

	def update(self, request, *args, **kwargs):
		self._shortid = request.data["shortid"]
		return super(UploadEventViewSet, self).update(request, *args, **kwargs)

	def get_object(self):
		return UploadEvent.objects.get(shortid=self._shortid)


class GameReplayDetail(RetrieveDestroyAPIView):
	queryset = GameReplay.objects.live()
	serializer_class = serializers.GameReplaySerializer
	lookup_field = "shortid"
	permission_classes = (IsOwnerOrReadOnly, )

	def perform_destroy(self, instance):
		instance.is_deleted = True
		instance.save()


class GameReplayList(ListAPIView):
	queryset = GameReplay.objects.live().prefetch_related("user", "global_game__players")
	serializer_class = serializers.GameReplayListSerializer

	def check_permissions(self, request):
		if not request.user.is_authenticated:
			self.permission_denied(request)
		return super().check_permissions(request)

	def get_queryset(self):
		queryset = super().get_queryset()
		user = self.request.user
		if not user.is_staff:
			# For non-staff, only own games are visible
			queryset = queryset.filter(user=user)
		# Allow filtering on username key
		username = self.request.query_params.get("username", None)
		if username:
			queryset = queryset.filter(user__username=username)
		return queryset


class CreateStatsSnapshotView(CreateAPIView):
	authentication_classes = (AuthTokenAuthentication, )
	permission_classes = (RequireAuthToken, )
	serializer_class = serializers.SnapshotStatsSerializer
