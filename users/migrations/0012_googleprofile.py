from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_alter_profile_contact_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='googleprofile',
            name='initial_username',
            field=models.CharField(blank=True, max_length=150),
        ),
    ]
