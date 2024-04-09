from django.urls import path
from api import views

urlpatterns = [
    path('', views.ApiOverview.as_view(), name="api-overview"),
    path('regions/', views.RegionList.as_view(), name="regions-list"),
    path('regions/<str:code>/', views.RegionDetail.as_view(),
         name="regions-details"),
    path('batches/', views.BatchList.as_view(), name="batches-list"),
    path('batches/<str:batch_id>/',
         views.BatchDetail.as_view(), name="batches-details"),
    path('jobs/', views.JobList.as_view(), name="jobs-list"),
    path('jobs/<int:pk>', views.JobDetails.as_view(), name="jobs-details"),
    path('jobspecs/', views.JobSpecsList.as_view(), name="jobspecs-list"),
    path('jobspecs/<int:pk>/', views.JobSpecsDetails.as_view(),
         name="jobspecs-details"),
    path('batch-jobs/', views.BatchJobList.as_view(), name="batchjobs-list"),
    path('jobs-by-batch/', views.BatchJobsByBatch.as_view(), name="batchjobs-bybatch"),
    path('jobs-queued/', views.BatchJobsQueued.as_view(), name="batchjobs-queued"),

    path("healthcheck/", views.healthcheck),
    path("metrics/", views.metrics)
]
