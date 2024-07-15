from clearcode.store_scans import store_scancode_scans_from_cd_items


class Command(BaseCommand):
    help = 'Store scancode scans in git repositories'

    def add_arguments(self, parser):
        parser.add_argument('work_dir', type=str)
        parser.add_argument('--github_org', type=str, default="")
        parser.add_argument('--count', type=int, default=0)

    def handle(self, *args, **options):
        store_scancode_scans_from_cd_items(work_dir=options['work_dir'], github_org=options['github_org'], count=options['count'])