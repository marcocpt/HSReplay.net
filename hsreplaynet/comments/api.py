from django_comments.models import Comment
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import RetrieveDestroyAPIView
from rest_framework.serializers import HyperlinkedModelSerializer
from hsreplaynet.api.permissions import IsOwnerOrStaff
from hsreplaynet.api.serializers import UserSerializer


class CommentSerializer(HyperlinkedModelSerializer):
	user = UserSerializer()

	class Meta:
		model = Comment
		fields = ("user", "comment", "submit_date")


class CommentDetailView(RetrieveDestroyAPIView):
	authentication_classes = (SessionAuthentication, )
	permission_classes = (IsOwnerOrStaff, )
	queryset = Comment.objects.filter(is_removed=False)
	serializer_class = CommentSerializer

	def perform_destroy(self, instance):
		instance.is_removed = True
		instance.save()
