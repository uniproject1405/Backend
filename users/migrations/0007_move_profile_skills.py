from django.db import migrations


def move_profile_skills(apps, schema_editor):
    Profile = apps.get_model('users', 'Profile')
    ProfileSkill = apps.get_model('users', 'ProfileSkill')

    for profile in Profile.objects.all():
        old_skills = profile.skills.all()

        for old_skill in old_skills:
            new_skill, created = ProfileSkill.objects.get_or_create(
                name=old_skill.name
            )

            profile.profile_skills.add(new_skill)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_profileskill_profile_profile_skills'),
    ]

    operations = [
        migrations.RunPython(
            move_profile_skills,
            migrations.RunPython.noop
        ),
    ]