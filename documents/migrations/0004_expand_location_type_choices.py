from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_damages_wages_to_textfield'),
    ]

    operations = [
        migrations.AlterField(
            model_name='incidentoverview',
            name='location_type',
            field=models.CharField(
                blank=True,
                max_length=30,
                choices=[
                    ('public_sidewalk', 'Public Sidewalk'),
                    ('public_park', 'Public Park'),
                    ('public_plaza', 'Public Plaza / Square'),
                    ('public_parking_lot', 'Public Parking Lot'),
                    ('roadway', 'Roadway / Highway'),
                    ('traffic_stop', 'Traffic Stop (roadside)'),
                    ('police_station', 'Police Station / Lobby'),
                    ('sheriff_office', "Sheriff's Office / Lobby"),
                    ('courthouse', 'Courthouse / Lobby'),
                    ('city_hall', 'City / Town Hall'),
                    ('county_building', 'County Government Building'),
                    ('federal_building', 'Federal Building'),
                    ('dmv', 'DMV / Motor Vehicle Office'),
                    ('post_office', 'Post Office'),
                    ('government_office', 'Other Government Office / Building'),
                    ('public_school', 'Public School'),
                    ('public_library', 'Public Library'),
                    ('public_hospital', 'Public Hospital / Clinic'),
                    ('jail', 'Jail / Detention Center'),
                    ('prison', 'Prison / Correctional Facility'),
                    ('airport', 'Airport / Terminal'),
                    ('transit_station', 'Train / Bus Station'),
                    ('transit_vehicle', 'Bus / Train / Transit Vehicle'),
                    ('personal_vehicle', 'Personal Vehicle'),
                    ('private_residence', 'Private Residence'),
                    ('private_business', 'Private Business / Store'),
                    ('other', 'Other'),
                ],
            ),
        ),
    ]
