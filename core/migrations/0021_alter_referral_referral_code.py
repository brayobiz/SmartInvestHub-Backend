# Generated by Django 5.2 on 2025-05-22 10:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_alter_referral_referral_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referral',
            name='referral_code',
            field=models.CharField(default='c2a6700eb432', max_length=12, unique=True),
        ),
    ]
