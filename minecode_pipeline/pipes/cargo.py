from packageurl import PackageURL
from aboutcode.hashid import get_core_purl
from minecode_pipeline.pipes import write_purls_to_repo


def collect_packages_from_cargo(packages, repo, push_commit=False):
    """Collect Cargo package versions into purls and write them to the repo."""

    if not packages and len(packages) > 0:
        raise ValueError("No packages found")

    updated_purls = []
    first_pkg = packages[0]
    version = first_pkg.get("vers")
    name = first_pkg.get("name")
    purl = PackageURL(type="cargo", name=name, version=version)
    base_purl = get_core_purl(purl)

    for package in packages:
        version = package.get("vers")
        name = package.get("name")

        purl = PackageURL(type="cargo", name=name, version=version).to_string()
        updated_purls.append(purl)

    write_purls_to_repo(repo, base_purl, packages, push_commit)
