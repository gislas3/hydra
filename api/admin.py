from django.contrib import admin


from .models import Batch, Region, Batch_Job

admin.site.register(Batch)
admin.site.register(Region)
admin.site.register(Batch_Job)

