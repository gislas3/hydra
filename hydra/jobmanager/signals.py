from django.dispatch import receiver
from django.db.models.signals import post_save
import logging
from api.models import Batch
from hydra.jobmanager.jobmanager import JobManager
import os



@receiver(post_save, sender=Batch)
def on_callback_from_batch(instance, *args, **kwargs):
    """
        Based on Django Signals. This method will be called every time a new `Batch_Photo` is saved to the database
        :param instance: The actual instance that have been saved to the database
    """
    logging.debug("Signal received, a batch was saved")
    batch_obj = instance
    batch_id = batch_obj.batch_id
    logging.info("Hydra received batch with id: %s . Starting to process", str(batch_id))
    job_manager = JobManager()
    job_manager.on_add_batch_event(batch=batch_obj)



# @receiver(post_save, sender=Batch_Job)
# def on_callback_from_batch_job(instance,*args,**kwargs):
#     """
#         Based on Django Signals. This method will be called every time a new `Batch_Job` is saved to the database
#         :param instance: The actual instance that have been saved to the database
#     """
#     # TODO: Is this needed or will it be handled by Anders' job "watcher"?
#     logging.debug("Signal received, a batch_job was saved")
#     batch_obj = instance
#     # batch_id = batch_obj.batch_id
#     # logging.debug("BATCH_id in callback from batch job is: " + str(batch_id))
#     if batch_obj.job_spec.trigger_children:
#         data_type = batch_obj.job_spec.job_definition.data_type.data_type
#         if data_type == Job_DataType.IMU:
#             manager = IMUJobManager()
#             manager.on_save_batch_job_event(batch_obj)
#         elif data_type == Job_DataType.PHOTO:
#             manager = PhotoJobManager()
#             manager.on_save_batch_job_event(batch_obj)
#     # imu_manager = IMUJobManager(max_active_jobs=10)

#     # imu_manager.on_add_batch_event(batch_data=batch_obj)
