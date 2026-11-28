from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_profileskill_name_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX unique_auth_user_username_ci
                ON auth_user (LOWER(username));
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS unique_auth_user_username_ci;
            """
        ),
    ]
