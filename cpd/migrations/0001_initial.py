# Generated by Django 4.1.5 on 2023-12-28 23:00

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ClientPartnerInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=50, verbose_name='Tên đầy đủ')),
                ('phone', models.IntegerField(unique=True, verbose_name='Điện thoại')),
                ('email', models.EmailField(max_length=100)),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')),
                ('address', models.CharField(blank=True, max_length=100, null=True, verbose_name='Địa chỉ')),
                ('birthday', models.DateField(blank=True, null=True, verbose_name='Ngày sinh')),
                ('note', models.CharField(blank=True, max_length=200, null=True, verbose_name='Ghi chú')),
                ('company', models.CharField(max_length=50, verbose_name='Công ty')),
                ('rank', models.CharField(choices=[('1', '1'), ('2', '2'), ('3', '3')], max_length=4, verbose_name='Cấp')),
                ('commission', models.IntegerField(default=0.3, verbose_name='Tỷ lệ chia hoa hồng')),
            ],
            options={
                'verbose_name': 'Đối tác giới thiệu KH',
                'verbose_name_plural': 'Đối tác giới thiệu KH',
            },
        ),
    ]
