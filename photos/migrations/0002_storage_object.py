from django.db import migrations, models
import django.db.models.deletion
import photos.models


def register_existing_local_photos(apps, schema_editor):
    WeddingPhoto = apps.get_model("photos", "WeddingPhoto")
    StoredObject = apps.get_model("integrations", "StoredObject")

    for photo in WeddingPhoto.objects.exclude(image="").filter(storage_object__isnull=True).iterator():
        record = StoredObject.objects.filter(
            source_app="photos",
            source_model="WeddingPhoto",
            source_object_id=photo.public_id,
            status="AVAILABLE",
        ).first()
        if record is None:
            record = StoredObject.objects.create(
                wedding_id=photo.wedding_id,
                backend="LOCAL",
                category="PHOTO",
                relative_path=str(photo.image),
                mime_type=photo.mime_type or "",
                size_bytes=photo.file_size or 0,
                source_app="photos",
                source_model="WeddingPhoto",
                source_object_id=photo.public_id,
                status="AVAILABLE",
                created_by_id=photo.uploaded_by_id,
            )
        photo.storage_object_id = record.pk
        photo.save(update_fields=["storage_object"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0001_initial"),
        ("photos", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="weddingphoto",
            name="image",
            field=models.FileField(blank=True, upload_to=photos.models.photo_upload_to),
        ),
        migrations.AddField(
            model_name="weddingphoto",
            name="storage_object",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="wedding_photo",
                to="integrations.storedobject",
            ),
        ),
        migrations.RunPython(register_existing_local_photos, noop_reverse),
    ]
