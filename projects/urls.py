from django.urls import path
from .views import (
    ProjectListCreateView,
    ProjectDetailView,
    MyProjectsView,
    ExploreProjectsView,
    ProjectMembersListView,
    ProjectMemberDetailView,
)

urlpatterns = [
    path('', ProjectListCreateView.as_view(), name='project-list-create'),
    path('my/', MyProjectsView.as_view(), name='my-projects'),
    path('explore/', ExploreProjectsView.as_view(), name='project-explore'),

    path('<uuid:public_id>/', ProjectDetailView.as_view(), name='project-detail'),
    path('<uuid:public_id>/members/', ProjectMembersListView.as_view(), name='project-members'),
    path('<uuid:public_id>/members/<int:user_id>/', ProjectMemberDetailView.as_view(), name='project-member-detail'),
]
