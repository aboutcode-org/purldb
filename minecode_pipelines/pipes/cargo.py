from pathlib import Path

from aboutcode import hashid
from packageurl import PackageURL
from aboutcode.hashid import get_core_purl

from minecode_pipelines.pipes import write_data_to_yaml_file


def store_cargo_packages(packages, repo):
    """Collect Cargo package versions into purls and write them to the repo."""

    if not packages:
        return

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

    ppath = hashid.get_package_purls_yml_file_path(base_purl)
    purl_file_full_path = Path(repo.working_dir) / ppath
    write_data_to_yaml_file(path=purl_file_full_path, data=updated_purls)
    return purl_file_full_path, base_purl
