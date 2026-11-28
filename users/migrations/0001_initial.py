import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GoogleProfile',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID'
                )),
                ('google_id', models.CharField(
                    db_index=True,
                    max_length=255,
                    unique=True
                )),
                ('picture', models.URLField(
                    blank=True,
                    max_length=500
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='google_profile',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Google Profile',
                'verbose_name_plural': 'Google Profiles',
            },
        ),

        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID'
                )),
                ('name', models.CharField(blank=True, max_length=100)),
                ('bio', models.TextField(blank=True)),
                ('avatar', models.ImageField(
                    blank=True,
                    null=True,
                    upload_to='avatars/'
                )),
                ('contact_links', models.JSONField(
                    blank=True,
                    default=list
                )),
                ('open_to_collaboration', models.BooleanField(default=False)),
                ('open_to_mentoring', models.BooleanField(default=False)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
        ),
    ]