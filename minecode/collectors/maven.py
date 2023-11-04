from dateutil.parser import parse as dateutil_parse
from minecode.visitors.maven import get_artifacts, is_worthy_artifact, build_url_and_filename
from packagedcode.maven import get_urls
from minecode.utils import fetch_http, get_temp_file
from packagedcode.models import PackageData


MAVEN_INDEX_URL = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz'


class MavenNexusCollector:
    """
    Download and process a Nexus Maven index file.
    WARNING: Processing is rather long: a full index is ~600MB.
    """

    def fetch_index(self, uri=MAVEN_INDEX_URL, timeout=10):
        """
        Return a temporary location where the fetched content was saved.
        Does not return the content proper as a regular fetch does.

        `timeout` is a default timeout.
        """
        content = fetch_http(uri, timeout=timeout)
        temp_file = get_temp_file('NonPersistentHttpVisitor')
        with open(temp_file, 'wb') as tmp:
            tmp.write(content)
        return temp_file

    def get_packages(self, content=None):
        """
        Yield Package objects from maven index
        """
        if content:
            index_location = content
        else:
            index_location = self.fetch_index()

        artifacts = get_artifacts(index_location, worthyness=is_worthy_artifact)

        for artifact in artifacts:
            # we cannot do much without these
            group_id = artifact.group_id
            artifact_id = artifact.artifact_id
            version = artifact.version
            extension = artifact.extension

            if not (group_id and artifact_id and version and extension):
                continue

            qualifiers = {}
            if extension and extension != 'jar':
                qualifiers['type'] = extension

            classifier = artifact.classifier
            if classifier:
                qualifiers['classifier'] = classifier

            # FIXME: also use the Artifact.src_exist flags too?

            # build a URL: This is the real JAR download URL
            # FIXME: this should be set at the time of creating Artifacts
            # instead togther with the filename... especially we could use
            # different REPOs.
            jar_download_url, _ = build_url_and_filename(
                group_id, artifact_id, version, extension, classifier)

            # FIXME: should this be set in the yielded URI too
            last_mod = artifact.last_modified

            urls = get_urls(
                namespace=group_id,
                name=artifact_id,
                version=version,
                qualifiers=qualifiers or None,
            )

            repository_homepage_url = urls['repository_homepage_url']
            repository_download_url = urls['repository_download_url']
            api_data_url = urls['api_data_url']

            yield PackageData(
                type='maven',
                namespace=group_id,
                name=artifact_id,
                version=version,
                qualifiers=qualifiers or None,
                download_url=jar_download_url,
                size=artifact.size,
                sha1=artifact.sha1,
                release_date=last_mod,
                repository_homepage_url=repository_homepage_url,
                repository_download_url=repository_download_url,
                api_data_url=api_data_url,
            )
