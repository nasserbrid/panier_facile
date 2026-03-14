from django.db import migrations
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_user_stripe_customer_id_user_stripe_subscription_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(
                blank=True,
                max_length=128,
                null=True,
                region=None,
                verbose_name='Numéro de téléphone',
            ),
        ),
    ]
