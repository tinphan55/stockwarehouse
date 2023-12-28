from django.db import models

# Create your models here.

class ClientPartnerInfo (models.Model):
    RANK_CHOICES = [
        ('1', '1'),
        ('2', '2'),
        ('3','3'),
    ]
    full_name = models.CharField(max_length= 50, verbose_name='Tên đầy đủ')
    phone = models.IntegerField(null=False, verbose_name='Điện thoại', unique=True)
    email = models.EmailField(max_length=100)
    created_date = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    address = models.CharField(max_length=100, null= True, blank = True, verbose_name='Địa chỉ')
    birthday = models.DateField(null=True, blank = True, verbose_name='Ngày sinh')
    note =  models.CharField(max_length= 200,null=True, blank = True, verbose_name='Ghi chú')
    company = models.CharField(max_length= 50,null=True, blank=True, verbose_name='Công ty')
    rank= models.CharField(max_length=4,choices=RANK_CHOICES, null=False, blank=False,verbose_name = 'Cấp')
    commission = models.FloatField(default = 0.3, verbose_name='Tỷ lệ chia hoa hồng')
    class Meta:
        verbose_name = 'Đối tác giới thiệu KH'
        verbose_name_plural = 'Đối tác giới thiệu KH'

    def __str__(self):
        return str(self.full_name) + '_' + str(self.pk)
    
    def save(self, *args, **kwargs):
        if self.rank ==1:
            self.commission = 0.3
        elif self.rank ==2:
            self.commission = 0.5
        else:
            self.commission =0.7
        super(ClientPartnerInfo, self).save(*args, **kwargs)
    

    

