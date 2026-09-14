from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("gifts", "0003_return_gift_inventory"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="giftpaymentmethod",
            name="unique_gift_payment_method_name_per_wedding",
        ),
    ]
