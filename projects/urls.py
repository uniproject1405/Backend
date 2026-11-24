from django.urls import path
from .views import (
    ProjectListCreateView,
    ProjectDetailView,
    MyProjectsView,
    ExploreProjectsView,
    ProjectMembersView,
)

urlpatterns = [
    path('', ProjectListCreateView.as_view(), name='project-list-create'),
    path('my/', MyProjectsView.as_view(), name='my-projects'),
    path('explore/', ExploreProjectsView.as_view(), name='project-explore'),
    path('<int:pk>/members/', ProjectMembersView.as_view(), name='project-members'),
    path('<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
]