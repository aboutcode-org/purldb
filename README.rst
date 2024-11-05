The purldb
==========
This repo consists of these main tools:

- PackageDB that is the reference model (based on ScanCode toolkit)
  that contains package data with purl (Package URLs) being a first
  class citizen.
- MineCode that contains utilities to mine package repositories
- MatchCode that contains utilities to index package metadata and resources for
  matching
- MatchCode.io that provides package matching functionalities for codebases
- ClearCode that contains utilities to mine Clearlydefined for package data
- purldb-toolkit CLI utility and library to use the PurlDB, its API and various
  related libraries.

These are designed to be used first for reference such that one can query for
packages by purl and validate purl existence.

In the future, the collected packages will be used as reference for dependency
resolution, as a reference knowledge base for all package data, as a reference
for vulnerable range resolution and more.

Documentation
-------------

See https://aboutcode.readthedocs.io/projects/PURLdb/en/latest/ for PurlDB
documentation.


Acknowledgements, Funding, Support and Sponsoring
--------------------------------------------------------

This project is funded, supported and sponsored by:

- Generous support and contributions from users like you!
- the European Commission NGI programme
- the NLnet Foundation 
- the Swiss State Secretariat for Education, Research and Innovation (SERI)
- Google, including the Google Summer of Code and the Google Seasons of Doc programmes
- Mercedes-Benz Group
- Microsoft and Microsoft Azure
- AboutCode ASBL
- nexB Inc. 



|europa|   |dgconnect| 

|ngi|   |nlnet|   

|aboutcode|  |nexb|


This project was funded through the NGI0 Discovery Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 825322.

|ngidiscovery| https://nlnet.nl/project/vulnerabilitydatabase/



This project is funded through the NGI0 Entrust Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101069594.

|ngizeroentrust| https://nlnet.nl/project/FederatedSoftwareMetadata/


This project was funded through the NGI0 Commons Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101135429. Additional
funding is made available by the Swiss State Secretariat for Education, Research and Innovation
(SERI). 

|ngizerocommons| |swiss| https://nlnet.nl/project/FederatedCodeNext/


This project was funded through the NGI0 Entrust Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101069594. 

|ngizeroentrust| https://nlnet.nl/project/Back2source/


This project was funded through the NGI0 Core Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101092990.

|ngizerocore| https://nlnet.nl/project/Back2source-next/


This project was funded through the NGI0 Core Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101092990. 

|ngizerocore| https://nlnet.nl/project/FastScan/


This project was funded through the NGI0 Commons Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101135429. Additional
funding is made available by the Swiss State Secretariat for Education, Research and Innovation
(SERI).

|ngizerocommons| |swiss| https://nlnet.nl/project/MassiveFOSSscan/


This project was funded through the NGI Assure Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 957073.

|ngiassure| https://nlnet.nl/project/FOSS-supplychain/


This project was funded through the NGI0 Entrust Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101069594.

|ngizeroentrust| https://nlnet.nl/project/FOSS-supplychain-II/


This project was funded through the NGI0 Entrust Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101069594. 

|ngizeroentrust| https://nlnet.nl/project/purl2all/


This project was funded through the NGI0 Entrust Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101069594. 

|ngizeroentrust| https://nlnet.nl/project/purl2sym/


.. |nlnet| image:: https://nlnet.nl/logo/banner.png
    :target: https://nlnet.nl
    :height: 50
    :alt: NLnet foundation logo

.. |ngi| image:: https://ngi.eu/wp-content/uploads/thegem-logos/logo_8269bc6efcf731d34b6385775d76511d_1x.png
    :target: https://ngi.eu35
    :height: 50
    :alt: NGI logo

.. |nexb| image:: https://nexb.com/wp-content/uploads/2022/04/nexB.svg
    :target: https://nexb.com
    :height: 30
    :alt: nexB logo

.. |europa| image:: https://ngi.eu/wp-content/uploads/sites/77/2017/10/bandiera_stelle.png
    :target: http://ec.europa.eu/index_en.htm
    :height: 40
    :alt: Europa logo

.. |aboutcode| image:: https://aboutcode.org/wp-content/uploads/2023/10/AboutCode.svg
    :target: https://aboutcode.org/
    :height: 30
    :alt: AboutCode logo

.. |swiss| image:: https://www.sbfi.admin.ch/sbfi/en/_jcr_content/logo/image.imagespooler.png/1493119032540/logo.png
    :target: https://www.sbfi.admin.ch/sbfi/en/home/seri/seri.html
    :height: 40
    :alt: Swiss logo

.. |dgconnect| image:: https://commission.europa.eu/themes/contrib/oe_theme/dist/ec/images/logo/positive/logo-ec--en.svg
    :target: https://commission.europa.eu/about-european-commission/departments-and-executive-agencies/communications-networks-content-and-technology_en
    :height: 40
    :alt: EC DG Connect logo

.. |ngizerocore| image:: https://nlnet.nl/image/logos/NGI0_tag.svg
    :target: https://nlnet.nl/core
    :height: 40
    :alt: NGI Zero Core Logo

.. |ngizerocommons| image:: https://nlnet.nl/image/logos/NGI0_tag.svg
    :target: https://nlnet.nl/commonsfund/
    :height: 40
    :alt: NGI Zero Commons Logo

.. |ngizeropet| image:: https://nlnet.nl/image/logos/NGI0PET_tag.svg
    :target: https://nlnet.nl/PET
    :height: 40
    :alt: NGI Zero PET logo

.. |ngizeroentrust| image:: https://nlnet.nl/image/logos/NGI0Entrust_tag.svg
    :target: https://nlnet.nl/entrust
    :height: 38
    :alt: NGI Zero Entrust logo

.. |ngiassure| image:: https://nlnet.nl/image/logos/NGIAssure_tag.svg
    :target: https://nlnet.nl/image/logos/NGIAssure_tag.svg
    :height: 32
    :alt: NGI Assure logo

.. |ngidiscovery| image:: https://nlnet.nl/image/logos/NGI0Discovery_tag.svg
    :target: https://nlnet.nl/discovery/
    :height: 40
    :alt: NGI Discovery logo






