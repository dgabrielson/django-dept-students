#######################
from __future__ import print_function, unicode_literals

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ...models import RequirementTag

#######################


class Command(BaseCommand):
    args = ""
    help = "Update the database with the currently configured requirement tags."

    def handle(self, *args, **options):
        """
        Do the command!
        """
        tags = []
        try:
            requirements = settings.STUDENTS_REGISTRATION_REQUIREMENTS
        except AttributeError:
            raise CommandError(
                "Add STUDENTS_REGISTRATION_REQUIREMENTS to your settings."
            )

        for label, form, template in requirements:
            tag, created = RequirementTag.objects.get_or_create(label=label)
            if created:
                print("Added RequirementTag:", label, file=self.stdout)
            if not tag.active:
                tag.active = True
                tag.save()
                print("Reactivated RequirementTag:", label, file=self.stdout)
            tags.append(label)
        for tag in RequirementTag.objects.exclude(label__in=tags):
            tag.active = False
            tag.save()
            print("Deactivating RequirementTag:", tag.label, file=self.stdout)
