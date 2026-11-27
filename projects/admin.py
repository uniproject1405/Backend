from django.contrib import admin
from .models import Skill, SkillAlias, Project, ProjectMember


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1
    autocomplete_fields = ['user']
    readonly_fields = ['joined_at']


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(SkillAlias)
class SkillAliasAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'skill')
    list_filter = ('skill',)
    search_fields = ('name', 'skill__name')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'creator', 'capacity', 'current_members_count', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description', 'creator__username', 'creator__email')
    filter_horizontal = ('skills',)
    inlines = [ProjectMemberInline]
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description="Members")
    def current_members_count(self, obj):
        return obj.members.count()


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'user', 'joined_at')
    list_filter = ('joined_at', 'project')
    search_fields = ('project__title', 'user__username', 'user__email')
    readonly_fields = ('joined_at',)
