from django.db import models
import uuid


class Batch(models.Model):
    """
    Model which defines general batches. Can be identified by batch_id
    (which links to a batch of data uploaded by an arbitrary sensor).
    """
    batch_id = models.UUIDField(
        primary_key=True, editable=False, unique=True)
    device_id = models.UUIDField(null=True,
        default=None,
        help_text="The id of the device which recorded the device")
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Time batch information was first sent to this server.")
    updated_at = models.DateTimeField(
        null=True,
        default=None,
        help_text="Time batch information was first sent to this server.")
    region = models.ForeignKey(
        'Region',
        on_delete=models.CASCADE,
        help_text="Region that batch came from."
    )

    def __str__(self):
        return str(self.batch_id)


class Region(models.Model):
    """
    Region information is stored due to current strategy of splitting data by
    regions. Contains an ID, a description, and a namespace.
    """
    code = models.CharField(
        max_length=255, db_index=True, unique=True)  # eg EU.NI
    description = models.CharField(max_length=255, null=False, blank=True)
    # TODO: See if namespace is needed or not
    namespace = models.CharField(
        max_length=255,
        null=False,
        blank=True,
        help_text="Kubernetes namespace."
    )

    def __str__(self):
        return str(self.id)


class Job_Definition(models.Model):

    """
    This table will be used to store the defining features of jobs, such as
    their name, the type of data they should be performed on, and what possible
    jobs they depend upon.
    """
    name = models.CharField(max_length=255, null=False,
                            blank=False, db_index=True)
    description = models.CharField(max_length=255, null=False, blank=True)
    # TODO: Right now, there is no possibility for a job to have multiple
    # direct parents. Is this a safe assumption?
    parent_job = models.ForeignKey(
        'Job_Definition',
        default=None,
        help_text="Possible parent job",
        null=True,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return str(self.id)


class Job_Spec(models.Model):
    """
    Table used to store the specification of a job. Contains the information
    about how much data the job should process at once, what container image
    it is linked to, the namespace, and whether or not it is an active job spec
    """

    AMAZON = 'AWS'
    AZURE = 'AZ'

    RUN_ENVIRONMENTS = [
        (AMAZON, 'Amazon'),
        (AZURE, 'Azure'),
    ]

    GREG = 'greg'
    CHARLOTTE = 'charlotte'
    TIRTHA = 'tirtha'
    ANDERS = 'anders'
    JENS = 'jens'
    CHRIS = 'chris'
    KEVIN = 'kevin'
    JOHN = 'john'
    USERS = [(GREG, 'greg@mobilizedconstruction.com'),
             (CHARLOTTE, 'charlotte@mobilizedconstruction.com'),
             (TIRTHA, 'tirtha@mobilizedconstruction.com'),
             (ANDERS, 'anders@mobilizedconstruction.com'),
             (JENS, 'jens@mobilizedconstruction.com'),
             (CHRIS, 'chris@mobilizedconstruction.com'),
             (KEVIN, 'kevin@mobilizedconstruction.com'),
             ]

    job_definition = models.ForeignKey(
        'Job_Definition',
        null=False,
        help_text="The job associated with this Job Priority",
        on_delete=models.CASCADE,
    )
    run_environment = models.CharField(
        max_length=3,
        choices=RUN_ENVIRONMENTS,
        null=False,
        blank=False,
        help_text="The environment which the job should be run in",
    )
    container_image = models.TextField(
        blank=False,
        null=False,
        help_text="The container linked to this job spec",
    )
    priority = models.PositiveSmallIntegerField(
        null=False,
        default=0,
        help_text="Optional priority for potentially ordering jobs",
    )
    active = models.BooleanField(
        default=True,
        null=False,
        help_text="Flag denoting whether job is active",
    )
    namespace = models.CharField(
        max_length=255,
        null=False,
        blank=False,
    )
    time_limit = models.DurationField(
        null=False,
        help_text="The max duration of the job.",
    )
    trigger_children = models.BooleanField(
        default=False,
        null=False,
        help_text="Flag denoting whether to trigger subsequent jobs",
    )
    data_threshold = models.PositiveIntegerField(
        null=False,
        help_text="The maximum amount of data to process in the job"
    )
    created_by = models.CharField(
        max_length=20, choices=USERS, default=GREG, help_text='The user who defined the job spec')
    environment_variables = models.JSONField(default=dict, null=True)
    k8s_job_labels = models.JSONField(default=dict, null=True)
    init_photo_container = models.BooleanField(
        default=False,
        null=False,
        help_text="Is a init photo container needed for this job",
    )
    whitelisted_devices = models.JSONField(default=list, 
    null=False, 
    help_text="The devices (WHICH SHOULD BE A LIST IN JSON FORMAT) that are allowed to trigger this job. Default is an empty list, which means that ALL devices will trigger this job.")


# Since can possibly be linked to photo and accelerometer data, will only
# be one table
class Batch_Job(models.Model):
    """
    Defines the relationship between jobs and batches, i.e. keeps track of
    what jobs are run with what batch.
    """
    job_spec = models.ForeignKey(
        'Job_Spec',
        null=False,
        help_text="The job spec defining this batch job.",
        on_delete=models.CASCADE
    )
    scheduled = models.BooleanField(
        default=False,
        help_text="Flag denoting whether the job has been scheduled"
    )

    created_on_k8s = models.BooleanField(
        default=False,
        help_text="Flag denoting whether the job has been created on k8s."
    )

    started = models.BooleanField(
        default=False,
        help_text="Flag denoting whether the job has been started."
    )
    finished = models.BooleanField(
        default=False,
        help_text="Flag denoting whether the job has terminated."
    )
    time_started = models.DateTimeField(
        null=True,
        default=None,
        help_text="The start time of the job, should be in UTC time."
    )
    succeeded = models.BooleanField(
        default=False,
        help_text="Flag denoting whether the job was successful or not."
    )
    tries = models.PositiveSmallIntegerField(
        default=0,
        null=False,
        help_text="The number of times the job has been attempted"
    )
    batches = models.ManyToManyField(Batch,
                                     help_text='The batches that this job took place on'
                                     )

