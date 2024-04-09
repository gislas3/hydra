from .settings import *

SECRET_KEY = os.environ.get("SECRET_KEY", "random_default_key")

DEBUG = True

# 'DJANGO_ALLOWED_HOSTS' should be a single string of hosts with a space between each.
# For example: 'DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]'
#ALLOWED_HOSTS = []
