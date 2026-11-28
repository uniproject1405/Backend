import uuid
from django.db import migrations


def populate_profile_data(apps, schema_editor):
    Profile = apps.get_model('users', 'Profile')

    for profile in Profile.objects.filter(public_id__isnull=True).iterator():
        profile.public_id = uuid.uuid4()
        profile.save(update_fields=['public_id'])

    Profile.objects.filter(job_title__isnull=True).update(job_title='')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_profile_job_title_profile_public_id_profile_skills_and_more'),
    ]

    operations = [
        migrations.RunPython(
            populate_profile_data,
            migrations.RunPython.noop,
        ),
    ]