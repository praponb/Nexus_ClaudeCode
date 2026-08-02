from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0002_asset_legal_hold"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="legal_hold",
            field=models.BooleanField(default=False),
        ),
    ]
