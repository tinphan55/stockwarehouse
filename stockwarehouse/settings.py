"""
Django settings for ecotrading project.

Generated by 'django-admin startproject' using Django 4.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

import os
from pathlib import Path
from .jazzmin import *
from datetime import timedelta, datetime as dt




# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-1@%_-7!z=r9nf#$rbge-n10+fs@9x)q8=b2o0qbl&8)n$%#x0x'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django_crontab',
    'jazzmin',
    'rest_framework',
    'debug_toolbar',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'operation',
    'infotrading',
    'dbbackup',
    'cpd',
    'realstockaccount',
    'regulations',
  
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware', 
    'django_auto_logout.middleware.auto_logout',
]

INTERNAL_IPS = ['127.0.0.1', 'localhost', '10.100.66.4']


ROOT_URLCONF = 'stockwarehouse.urls'

AUTO_LOGOUT = {
    'IDLE_TIME': timedelta(minutes=360),
    'REDIRECT_TO_LOGIN_IMMEDIATELY': True,
}


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'builtins': ['stockwarehouse.custom_filters'],  # Thay 'your_app_name' bằng tên ứng dụng của bạn
        },
    },
]

WSGI_APPLICATION = 'stockwarehouse.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases



DATABASES_LIST = [{
#server
      'default': {
         'ENGINE': 'django.db.backends.postgresql',
         'NAME': 'ecotrading',                      
         'USER': 'admin',
         'PASSWORD': 'Ecotr@ding2023',
         'HOST': 'localhost',
         'PORT': '',
     }
 }, 
#localhost



{
     'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ecotrading',                      
        'USER': 'postgres',
        'PASSWORD': 'Ecotrading2023',
        'HOST': 'localhost',
        'PORT': '5432',
    }
},
{
     'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',                      
        'USER': 'postgres',
        'PASSWORD': 'Ecotrading2024',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}]
DATABASES = DATABASES_LIST[0]

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/


LANGUAGE_CODE = 'vi'

# LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Ho_Chi_Minh'

USE_I18N = True

USE_L10N = False

USE_TZ = False

DATE_FORMAT = ( ( 'd-m-Y' ))
DATE_INPUT_FORMATS = ( ('%d-%m-%Y'),)
DATETIME_FORMAT = (( 'd-m-Y H:i' ))
DATETIME_INPUT_FORMATS = (('%d-%m-%Y %H:%i'),)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = Path.joinpath(BASE_DIR, 'static')
MEDIA_URL = '/media/'
MEDIA_ROOT = Path.joinpath(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
JAZZMIN_SETTINGS = JAZZMIN_SETTINGS
JAZZMIN_UI_TWEAKS = JAZZMIN_UI_TWEAKS

CRONTAB_TIMEZONE = 'Asia/Ho_Chi_Minh'

# Ví dụ cấu hình cho việc sao lưu vào thư mục 'backups/'
DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'

DBBACKUP_CLEANUP_KEEP = True
DBBACKUP_CLEANUP_KEEP_NUMBER = 3  # Số lượng bản sao lưu giữ lại
DBBACKUP_STORAGE_OPTIONS = {
    'location': '/root/web2/backup/', 
}



def custom_backup_filename(databasename, servername, extension,datetime, content_type):
    formatted_datetime = dt.now().strftime('%Y-%m-%d') 
    return f"{formatted_datetime}.{extension}"

DBBACKUP_FILENAME_TEMPLATE = custom_backup_filename

CRONJOBS = [
    ('0 1 * * *', 'stockwarehouse.schedule.schedule_morning'),# chạy lúc 7 giờ sáng
    ('0 */2 2-8 * 1-5', 'stockwarehouse.schedule.get_info_stock_price_filter'),# chạy từ 9 đến 15h, cách 2 giờ chạy 1 lần
    ('30 4 * * 1-5', 'stockwarehouse.schedule.schedule_mid_trading_date'),# chạy lúc 11h30 sáng
    # ('15 8 * * 1-5', 'stockwarehouse.schedule.schedule_after_trading_date'),# chạy lúc 14h45 trưa
    ('10-25/15 2-7 * * 1-5', 'stockwarehouse.schedule.get_info_stock_price_stock_68'),# từ 2:10 đến 7:25 mỗi ngày cách nhau 15p

]


