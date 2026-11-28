import uuid

from django.db import migrations, models


def generate_public_ids(apps, schema_editor):
    MembershipRequest = apps.get_model(
        'applications',
        'MembershipRequest'
    )

    for request in MembershipRequest.objects.filter(public_id__isnull=True):
        request.public_id = uuid.uuid4()
        request.save(update_fields=['public_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0002_membershiprequest_response_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershiprequest',
            name='public_id',
            field=models.UUIDField(
                null=True,
                editable=False
            ),
        ),
        migrations.RunPython(
            generate_public_ids,
            migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name='membershiprequest',
            name='public_id',
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False
            ),
        ),
    ]