# Generated by Django 5.1.6 on 2025-03-04 23:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_rename_photo_serversettings_logo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='is_lgbt',
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='major',
            field=models.CharField(blank=True, choices=[('AIM', 'Accounting'), ('ACTS', 'Actuarial Science'), ('AMS', 'American Studies'), ('ACN', 'Applied Cognition and Nsc.'), ('MAP', 'Applied Mathematics'), ('APHY', 'Applied Physics'), ('ASOC', 'Applied Sociology'), ('AP', 'Art and Performance'), ('ATCM', 'Arts, Technology, and Emerging'), ('AUD', 'Audiology'), ('BCHM', 'Biochemistry'), ('BCBM', 'Bioinform and Comput Biology'), ('BIO', 'Biology'), ('BMEN', 'Biomedical Engineering'), ('BMED', 'Biomedical Sciences'), ('BIOT', 'Biotechnology'), ('BA', 'Business Administration'), ('CHEM', 'Chemistry'), ('CLDP', 'Child Learning and Development'), ('CGNS', 'Cognition and Neuroscience'), ('CGS', 'Cognitive Science'), ('CMSD', 'Comm Sciences and Disorders'), ('COMD', 'Communication Disorders'), ('CE', 'Computer Engineering'), ('CS', 'Computer Science'), ('CRIM', 'Criminology'), ('ECON', 'Economics'), ('EEM', 'Elec Engineering-Microelectron'), ('EET', 'Elec Engineering-Telecommunic'), ('EE', 'Electrical Engineering'), ('EMAC', 'Emerging Media and Communicati'), ('EGM', 'Engineering Mathematics'), ('FIN', 'Finance'), ('GNDS', 'Gender Studies'), ('GEOG', 'Geography'), ('GEOS', 'Geosciences'), ('GIS', 'Geospatial Information Science'), ('GSIS', 'Geospatial Information Science'), ('GRU', 'Grad Limited UGRD Crse Only'), ('GRAD', 'Graduate Non-Degree'), ('EMGT', 'Graduate Non-Degree Exec'), ('HCMG', 'Healthcare Management'), ('HS', 'Historical Studies'), ('HIST', 'History'), ('HUSL', 'HUMA – Studies in Literature'), ('HDEC', 'Human Dev-Early Childhood Dis'), ('HUAS', 'Humanities-Aesthetic Studies'), ('HUHI', 'Humanities-History of Ideas'), ('HUMA', 'Humanities'), ('MITM', 'Info Technology and MGT'), ('IS', 'Interdisciplinary Studies'), ('IMS', 'International MGT Studies'), ('IPEC', 'International Political Econ'), ('LIT', 'Literary Studies'), ('MSC', 'Management Science'), ('MBC', 'Master of Bus Admin – Cohort'), ('EMBA', 'Master of Bus Admin – Exec'), ('MBA', 'Master of Business Admin'), ('MPA', 'Master of Public Affairs'), ('MPP', 'Master of Public Policy'), ('MSEN', 'Material Science and Engin'), ('MATH', 'Mathematical Sciences'), ('MED', 'Mathematics Education'), ('MBG', 'MBA – Global'), ('MECH', 'Mechanical Engineering'), ('MSPM', 'Mgmt and Admin Sci'), ('MAS', 'MGT and Admin Sciences'), ('BCM', 'Molecular and Cell Biology'), ('MB', 'Molecular Biology'), ('NSC', 'Neuroscience'), ('PHIL', 'Philosophy'), ('PHYS', 'Physics'), ('PSCL', 'Political Sci-Constitutnl Law'), ('PSLS', 'Political Sci-Legslatv Studies'), ('PSCI', 'Political Science'), ('PSYS', 'Psychological Sciences'), ('PSY', 'Psychology'), ('PA', 'Public Administration'), ('PAFF', 'Public Affairs'), ('PPPE', 'Public Policy and Political Ec'), ('SCE', 'Science Education'), ('SOC', 'Sociology'), ('SE', 'Software Engineering'), ('SPAU', 'Speech-Language Path and Aud'), ('STAT', 'Statistics'), ('SCMT', 'Supply Chain Management'), ('TED', 'Teacher Education'), ('TE', 'Telecommunications Engineering'), ('UND', 'Undecided'), ('UGS', 'Undergraduate Studies'), ('unknown', 'Unknown')], default=None, null=True),
        ),
    ]
