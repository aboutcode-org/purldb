from packageurl import PackageURL
from aboutcode.hashid import get_core_purl
from minecode_pipelines.pipes import write_purls_to_repo


def store_cargo_packages(packages, fed_repo, push_commit=False):
    """Collect Cargo package versions into purls and write them to the repo."""

    if not packages:
        raise ValueError("No packages found")

    first_pkg = packages[0]
    name = first_pkg.get("name")
    version = first_pkg.get("vers")
    purl = PackageURL(type="cargo", name=name, version=version)
    base_purl = get_core_purl(purl)

    updated_purls = []
    for package in packages:
        name = package.get("name")
        version = package.get("vers")
        purl = PackageURL(type="cargo", name=name, version=version).to_string()
        updated_purls.append(purl)

    write_purls_to_repo(fed_repo, base_purl, updated_purls, push_commit)
