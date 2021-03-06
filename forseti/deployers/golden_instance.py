from forseti.deployers.base import BaseDeployer
from forseti.models import GoldenEC2Instance
from forseti.utils import balloon_timer


class GoldenInstanceDeployer(BaseDeployer):
    """Deployer for ticketea's infrastructure"""

    name = "golden_instances"

    def __init__(self, application, configuration, command_args=None):
        super(GoldenInstanceDeployer, self).__init__(application, configuration, command_args)
        self.gold_instance = None

    def create_ami_from_golden_instance(self):
        """
        Create an AMI from a golden EC2 instance
        """
        self.gold_instance = GoldenEC2Instance(
            self.application,
            self.configuration.get_gold_instance_configuration(self.application)
        )

        self.gold_instance.launch_and_wait()
        self.gold_instance.provision(self.command_args)
        ami_id = self.gold_instance.create_image()
        self.gold_instance.terminate()
        self.gold_instance = None

        return ami_id

    def generate_ami(self):
        return self.create_ami_from_golden_instance()

    def setup_autoscale(self, ami_id):
        """
        Creates or updates the autoscale group, launch configuration, autoscaling
        policies and CloudWatch alarms.

        :param ami_id: AMI id used for the new autoscale system
        """
        group = super(GoldenInstanceDeployer, self).setup_autoscale(ami_id)

        print "Waiting until instances are up and running"
        group.apply_launch_configuration_for_deployment()
        print "All instances are running"

    def deploy(self, ami_id=None):
        """
        Do the code deployment in a golden instance and setup an autoscale group
        with an AMI created from it.

        :param ami_id: AMI id to be deployed. If it's `None`, a new one will be
                       created
        """
        with balloon_timer("") as balloon:
            if not ami_id:
                ami_id = self.create_ami_from_golden_instance()
                print "New AMI %s from golden instance" % ami_id
            self.setup_autoscale(ami_id)

        minutes, seconds = divmod(int(balloon.seconds_elapsed), 60)
        print "Total deployment time: %02d:%02d" % (minutes, seconds)
