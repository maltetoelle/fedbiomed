# Generated by Django 3.1.7 on 2021-03-15 18:04

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Upload',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to='uploads/%Y/%m/%d')),
                ('created_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]