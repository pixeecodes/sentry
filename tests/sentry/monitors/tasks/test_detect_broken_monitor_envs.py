import uuid
from datetime import timedelta

from django.utils import timezone

from sentry.constants import ObjectStatus
from sentry.grouping.utils import hash_from_values
from sentry.monitors.models import (
    CheckInStatus,
    Monitor,
    MonitorCheckIn,
    MonitorEnvBrokenDetection,
    MonitorEnvironment,
    MonitorIncident,
    MonitorStatus,
    MonitorType,
    ScheduleType,
)
from sentry.monitors.tasks.detect_broken_monitor_envs import detect_broken_monitor_envs
from sentry.testutils.cases import TestCase
from sentry.testutils.helpers.features import with_feature


class MonitorDetectBrokenMonitorEnvTaskTest(TestCase):
    def create_monitor_and_env(self):
        monitor = Monitor.objects.create(
            name="test monitor",
            organization_id=self.organization.id,
            project_id=self.project.id,
            type=MonitorType.CRON_JOB,
            config={
                "schedule": [1, "day"],
                "schedule_type": ScheduleType.INTERVAL,
                "failure_issue_threshold": 1,
                "max_runtime": None,
                "checkin_margin": None,
            },
        )
        monitor_environment = MonitorEnvironment.objects.create(
            monitor=monitor,
            environment_id=self.environment.id,
            status=MonitorStatus.OK,
        )
        return (monitor, monitor_environment)

    @with_feature("organizations:crons-broken-monitor-detection")
    def test_creates_broken_detection_no_duplicates(self):
        monitor, monitor_environment = self.create_monitor_and_env()

        first_checkin = MonitorCheckIn.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            project_id=self.project.id,
            status=CheckInStatus.ERROR,
            date_added=timezone.now() - timedelta(days=14),
        )
        incident = MonitorIncident.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            starting_checkin=first_checkin,
            starting_timestamp=first_checkin.date_added,
            grouphash=hash_from_values([uuid.uuid4()]),
        )

        for i in range(3, -1, -1):
            MonitorCheckIn.objects.create(
                monitor=monitor,
                monitor_environment=monitor_environment,
                project_id=self.project.id,
                status=CheckInStatus.ERROR,
                date_added=timezone.now() - timedelta(days=i),
            )

        detect_broken_monitor_envs()
        assert len(MonitorEnvBrokenDetection.objects.filter(monitor_incident=incident)) == 1

        # running the task again shouldn't create duplicates
        detect_broken_monitor_envs()
        assert len(MonitorEnvBrokenDetection.objects.filter(monitor_incident=incident)) == 1

    @with_feature("organizations:crons-broken-monitor-detection")
    def test_does_not_create_broken_detection_insufficient_duration(self):
        monitor, monitor_environment = self.create_monitor_and_env()

        first_checkin = MonitorCheckIn.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            project_id=self.project.id,
            status=CheckInStatus.ERROR,
            date_added=timezone.now() - timedelta(days=10),
        )
        incident = MonitorIncident.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            starting_checkin=first_checkin,
            starting_timestamp=first_checkin.date_added,
            grouphash=hash_from_values([uuid.uuid4()]),
        )

        for i in range(4):
            MonitorCheckIn.objects.create(
                monitor=monitor,
                monitor_environment=monitor_environment,
                project_id=self.project.id,
                status=CheckInStatus.ERROR,
                date_added=timezone.now() - timedelta(days=1),
            )

        detect_broken_monitor_envs()
        assert len(MonitorEnvBrokenDetection.objects.filter(monitor_incident=incident)) == 0

    @with_feature("organizations:crons-broken-monitor-detection")
    def test_does_not_create_broken_detection_insufficient_checkins(self):
        monitor, monitor_environment = self.create_monitor_and_env()

        first_checkin = MonitorCheckIn.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            project_id=self.project.id,
            status=CheckInStatus.ERROR,
            date_added=timezone.now() - timedelta(days=14),
        )
        incident = MonitorIncident.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            starting_checkin=first_checkin,
            starting_timestamp=first_checkin.date_added,
            grouphash=hash_from_values([uuid.uuid4()]),
        )

        for i in range(1, -1, -1):
            MonitorCheckIn.objects.create(
                monitor=monitor,
                monitor_environment=monitor_environment,
                project_id=self.project.id,
                status=CheckInStatus.ERROR,
                date_added=timezone.now() - timedelta(days=i),
            )

        detect_broken_monitor_envs()
        assert len(MonitorEnvBrokenDetection.objects.filter(monitor_incident=incident)) == 0

    def test_does_not_create_broken_detection_no_feature(self):
        monitor, monitor_environment = self.create_monitor_and_env()

        first_checkin = MonitorCheckIn.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            project_id=self.project.id,
            status=CheckInStatus.ERROR,
            date_added=timezone.now() - timedelta(days=14),
        )
        incident = MonitorIncident.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            starting_checkin=first_checkin,
            starting_timestamp=first_checkin.date_added,
            grouphash=hash_from_values([uuid.uuid4()]),
        )

        for i in range(3, -1, -1):
            MonitorCheckIn.objects.create(
                monitor=monitor,
                monitor_environment=monitor_environment,
                project_id=self.project.id,
                status=CheckInStatus.ERROR,
                date_added=timezone.now() - timedelta(days=i),
            )

        detect_broken_monitor_envs()
        assert len(MonitorEnvBrokenDetection.objects.filter(monitor_incident=incident)) == 0

    @with_feature("organizations:crons-broken-monitor-detection")
    def test_does_not_create_for_disabled_monitor(self):
        monitor, monitor_environment = self.create_monitor_and_env()
        monitor.status = ObjectStatus.DISABLED
        monitor.save()

        first_checkin = MonitorCheckIn.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            project_id=self.project.id,
            status=CheckInStatus.ERROR,
            date_added=timezone.now() - timedelta(days=14),
        )
        incident = MonitorIncident.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            starting_checkin=first_checkin,
            starting_timestamp=first_checkin.date_added,
            grouphash=hash_from_values([uuid.uuid4()]),
        )

        for i in range(4, -1, -1):
            MonitorCheckIn.objects.create(
                monitor=monitor,
                monitor_environment=monitor_environment,
                project_id=self.project.id,
                status=CheckInStatus.ERROR,
                date_added=timezone.now() - timedelta(days=i),
            )

        detect_broken_monitor_envs()
        assert len(MonitorEnvBrokenDetection.objects.filter(monitor_incident=incident)) == 0
