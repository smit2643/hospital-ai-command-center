from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientprofile",
            name="address_line1",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="address_line2",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="allergies",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="chronic_conditions",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="city",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="country",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="current_medications",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="emergency_contact_name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="emergency_contact_relation",
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="insurance_policy_number",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="insurance_provider",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="marital_status",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="occupation",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="postal_code",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="state",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
