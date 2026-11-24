import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_populate_profile_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='job_title',
            field=models.CharField(max_length=150),
        ),
        migrations.AlterField(
            model_name='profile',
            name='public_id',
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
            ),
        ),
    ]