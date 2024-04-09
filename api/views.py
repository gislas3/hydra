import datetime as dt
import json
import logging
import uuid
from collections import namedtuple
from json import JSONDecodeError
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.renderers import (
    BrowsableAPIRenderer,
    HTMLFormRenderer,
    JSONRenderer,

)
from django.http import HttpResponse
from django.views.decorators.http import require_GET


from .serializers import (
    RegionSerializer,
    BatchSerializer,
    JobSerializer,
    JobSpecSerializer,
    BatchJobSerializer
)
from .models import (
    Batch_Job,
    Job_Spec,
    Region,
    Batch,
    Job_Definition
)

def healthcheck(request):
    return HttpResponse("Ready to serve your needs!", status=200)

def _notify_houston(endpoint, data):
    if not hasattr(settings, "HOUSTON_URL") and not hasattr(settings, "HOUSTON_TOKEN"):
        logging.warning("Houston notification was skipped")
        return
    HOUSTON_BATCH_API = urljoin(settings.HOUSTON_URL, endpoint)
    try:
        response = requests.post(
            HOUSTON_BATCH_API,
            json=data,
            headers={"Authorization": f"Token {settings.HOUSTON_TOKEN}"},
            verify=settings.ROOT_CERT,
        )
        prefixed_data = {}
    except Exception as e:
        logging.warning("Houston request failed", extra={"exception": e})
        return
    if response.status_code == 201:
        for key, value in data.items():
            prefixed_data["houston_" + key] = value
        logging.info(
            "Houston notified",
            extra={
                "status_code": response.status_code,
                "endpoint": endpoint,
                "data": prefixed_data,
                "batch_id": data["batch"] if "batch" in data else "",
            },
        )
    else:
        try:
            data = json.loads(response.content)
            logging.error(
                "Houston request failed",
                extra={
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "error": str(data["batch"]) if "batch" in data else data
                }
              )
        except JSONDecodeError as e:
            error_msg = str("Could not parse json request")
            logging.error(
                error_msg,
                extra={
                      'data': response.content,
                      'exception': e
                    }
                )

@require_GET
def metrics(request):
    batches_count = Batch.objects.all().count()
    number_of_batch_jobs = Batch_Job.objects.all().count()
    number_of_failed_batch_jobs = Batch_Job.objects.filter(tries__gt=5, finished=False,scheduled=True,created_on_k8s=True,succeeded=False).count()
    number_of_running_batch_jobs = Batch_Job.objects.filter(started=True, created_on_k8s=True, finished=False, succeeded=False, tries__lt=6).count()

    # Videos
    number_of_videos = Batch_Job.objects.filter(job_spec=1, succeeded=True, finished=True).count()


    metrics = (
        "# TYPE hydra_batches_total counter\n"
        "# UNIT hydra_batches_total batches\n"
        "# HELP hydra_batches_total Total batches registered in Hydra.\n"
        f"hydra_batches_total {batches_count}\n"
        "# TYPE hydra_batch_jobs_total counter\n"
        "# UNIT hydra_batch_jobs_total batch_jobs\n"
        "# HELP hydra_batch_jobs_total Total batch jobs registered in Hydra.\n"
        f"hydra_batch_jobs_total {number_of_batch_jobs}\n"
        "# TYPE hydra_batch_jobs_failed_total counter\n"
        "# UNIT hydra_batch_jobs_failed_total batch_jobs\n"
        "# HELP hydra_batch_jobs_failed_total Total failed batch jobs registered in Hydra.\n"
        f"hydra_batch_jobs_failed_total {number_of_failed_batch_jobs}\n"
        "# TYPE hydra_batch_jobs_running gauge\n"
        "# UNIT hydra_batch_jobs_running batch_jobs\n"
        "# HELP hydra_batch_jobs_running Current running batch jobs registered in Hydra.\n"
        f"hydra_batch_jobs_running {number_of_running_batch_jobs}\n"
        "# TYPE hydra_batch_jobs_videos_total counter\n"
        "# UNIT hydra_batch_jobs_videos_total videos\n"
        "# HELP hydra_batch_jobs_videos_total Total videos processed by Hydra.\n"
        f"hydra_batch_jobs_videos_total {number_of_videos}\n"
        "#EOF\n"
    )
    return HttpResponse(metrics, content_type="text/plain")

class ApiOverview(APIView):
    """
    List all endpoints for this api
    """

    def get(self, request):
        api_urls = {
            'Region': '/regions/',
            'Batch': '/batches/',
            'Jobs': '/jobs/',
            'JobSpecs': '/jobspecs/'
        }
        return Response(api_urls)

class RegionList(generics.ListCreateAPIView):
    """
    List all Region, or create a new Region.
    """
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer, HTMLFormRenderer)


class RegionDetail(generics.RetrieveUpdateAPIView):
    """
        Retrieve or update a Region instance using region code
        (case sensitive).
    """
    queryset = Region.objects.all()
    lookup_field = 'code'
    serializer_class = RegionSerializer
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer, HTMLFormRenderer)


class BatchList(generics.ListCreateAPIView):
    """
    List all Batch, or create a new Batch.
    """
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer, HTMLFormRenderer)

    def post(self, request, *args, **kwargs):
        # if request is coming from the API HTMLFORM. Parse that from QueryDict to json
        if request.content_type.__contains__('multipart/form-data'):
            body = json.dumps(request.POST)
        else:
            body = request.body
        data = self._get_request_data(body)
        try:
            batch_id = data["batch_id"]
        except KeyError as e:
            error_msg = "Cant find key 'batch_id' in data"
            logging.error(
                error_msg,
                extra={
                    'data': str(data),
                    'exception': e
                    }
            )
            return HttpResponse(error_msg, status=400)

        try:
            _ = Batch.objects.get(pk=uuid.UUID(batch_id))
            # This is pretty hacky, probably should change when we have full-time developers to work on this
            new_request = namedtuple('request', ['data']) 
            new_request.data = {'batch_id': batch_id}
            bd = BatchDetail()
            res = bd.put(request=new_request)
        except Exception as e:
            res = super().post(request, *args, **kwargs)
            if res.status_code == 201:
                try:
                    batch_id = data["batch_id"]
                    houston_photo_data = {
                    "batch": batch_id,
                    "status": 3,
                    "completed": True,
                    }
                    houston_imu_data =  {
                    "batch": batch_id,
                    "status": 4,                
                    "completed": True,
                    }
                    _notify_houston("api/batch_statuses/", houston_photo_data)
                    _notify_houston("api/batch_statuses/", houston_imu_data)
                except Exception as e:
                    logging.warning("Failed sending houston data for batch", extra={"exception": e})

        return res

    def _get_request_data(self,body):
        try:
            data = json.loads(body)
        except JSONDecodeError as e:
            error_msg = str("Could not parse json request")
            exception = e
            status_code = 400
            logging.error(error_msg,
                          extra={
                              'data': body,
                              'exception': exception,
                              'batch_id': None
                          })
            return HttpResponse(error_msg, status=status_code)
        except Exception as e:
            # batch_id = data["batch_id"]
            error_msg = "Invalid batches request " # + str(batch_id)
            logging.error(error_msg,
                          extra={
                              'data': body,
                              'exception': e#,
                              # 'batch_id': batch_id
                          })
            return HttpResponse(error_msg, status=400)
        return data


class BatchDetail(generics.RetrieveUpdateAPIView):
    """
        Retrieve a Batch instance.

    """
    queryset = Batch.objects.all()
    lookup_field = 'batch_id'
    serializer_class = BatchSerializer
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer, HTMLFormRenderer)

    def put(self, request, *args, **kwargs):
        try:

            batch_id = request.data['batch_id']
            batch = Batch.objects.get(batch_id=batch_id)
            batch.updated_at = dt.datetime.now().replace(tzinfo=dt.timezone.utc)
            batch.save()
            batch_id = batch_id

            houston_photo_data = {
            "batch": batch_id,
            "status": 3,
            "completed": True,
            }
            houston_imu_data = {
            "batch": batch_id,
            "status": 4,
            "completed": True,
            }
            _notify_houston("api/batch_statuses/", houston_photo_data)
            _notify_houston("api/batch_statuses/", houston_imu_data)

        except Exception as e:
            logging.error("Invalid batch detail request", extra={'exception': e})
            return Response(status=400)

            
        return Response(status=200)
        

class JobSpecsList(generics.ListCreateAPIView):
    """
    List all Job_Specs, or create a new Job Spec.
    """
    queryset = Job_Spec.objects.all()
    serializer_class = JobSpecSerializer
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer, HTMLFormRenderer)


class JobSpecsDetails(generics.RetrieveUpdateAPIView):
    """
        Retrieve or update a JobSpec instance.

    """
    queryset = Job_Spec.objects.all()
    serializer_class = JobSpecSerializer
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer, HTMLFormRenderer)


class JobList(generics.ListCreateAPIView):
    """
        List all Job_Definitions, or create a new Job_Definition.
    """
    queryset = Job_Definition.objects.all()
    serializer_class = JobSerializer
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer, HTMLFormRenderer)


class JobDetails(generics.RetrieveUpdateAPIView):
    """
        Retrive or update a Job_Definition instance.
    """
    queryset = Job_Definition.objects.all()
    serializer_class = JobSerializer
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer, HTMLFormRenderer)


class BatchJobList(generics.ListAPIView):
    """
        List all batch jobs
    """
    queryset = Batch_Job.objects.all()
    serializer_class = BatchJobSerializer

class BatchJobsByBatch(APIView):

    def _get_pretty_job(self, batch_job):
        time_started = None
        if batch_job.time_started:
            time_started = batch_job.time_started.strftime("%Y-%m-%d %H:%M:%S")
        return {"job_name": batch_job.job_spec.job_definition.name, 
        "time_started": time_started}

    def _get_response(self, queued_jobs, active_jobs, successful_jobs, failed_jobs):
        response = {"Total_Jobs": len(queued_jobs) + len(active_jobs) + len(successful_jobs) + len(failed_jobs), 
        "Queued_Jobs": {"Total": len(queued_jobs), "Job_List": queued_jobs},
        "Active_Jobs": {"Total": len(active_jobs), "Job_List": active_jobs}, 
        "Successful_Jobs": {"Total": len(successful_jobs), "Job_List": successful_jobs}, 
        "Failed_Jobs": {"Total": len(failed_jobs), "Job_List": failed_jobs}}
        return response


    def get(self, request):
        try:
            batch_id = uuid.UUID(request.query_params['batch_id'])
        except Exception as e:
            return Response(data={"Message": "Invalid batch_id requested"}, status=400)
        try:
            batch = Batch.objects.get(batch_id=batch_id)
        except Exception as e:
            return Response(data={"Message": "Batch doesn't exist"}, status=400)

        batch_jobs = batch.batch_job_set.all()
        queued_jobs = []
        active_jobs = []
        successful_jobs = []
        failed_jobs = []
        for bj in batch_jobs:
            bj_pretty = self._get_pretty_job(bj)
            if not bj.scheduled:
                queued_jobs.append(bj_pretty)
            elif bj.succeeded:
                successful_jobs.append(bj_pretty)
            elif not bj.finished:
                active_jobs.append(bj_pretty)
            else:
                failed_jobs.append(bj_pretty)
        final_response = self._get_response(queued_jobs, active_jobs, successful_jobs, failed_jobs)
        return Response(data=final_response, status=200)
    
class BatchJobsQueued(APIView):

    def get(self, request):
        return Response(status=200, data={"Total Queued Jobs": Batch_Job.objects.filter(scheduled=False, job_spec__active=True).count()})
        