from pkg_resources import resource_string
import yaml

METS_XML_EMPTY = resource_string(__name__, 'mets-empty.xml')
OCRD_TOOL_SCHEMA = yaml.load(resource_string(__name__, 'yaml-files/ocrd_tool.schema.yml'))
OCRD_BAGIT_PROFILE = yaml.load(resource_string(__name__, 'yaml-files/bagit-profile.yml'))
OCRD_BAGIT_PROFILE_URL = 'https://ocr-d.github.io/bagit-profile.json'

BAGIT_TXT = 'BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8'

NAMESPACES = {
    'mets': "http://www.loc.gov/METS/",
    'mods': "http://www.loc.gov/mods/v3",
    'xlink': "http://www.w3.org/1999/xlink",
    'page': "http://schema.primaresearch.org/PAGE/gts/pagecontent/2017-07-15",
    'xsl': 'http://www.w3.org/1999/XSL/Transform#',
}

# pylint: disable=bad-whitespace
TAG_METS_AGENT            = '{%s}agent' % NAMESPACES['mets']
TAG_METS_DIV              = '{%s}div' % NAMESPACES['mets']
TAG_METS_FILE             = '{%s}file' % NAMESPACES['mets']
TAG_METS_FILEGRP          = '{%s}fileGrp' % NAMESPACES['mets']
TAG_METS_FILESEC          = '{%s}fileSec' % NAMESPACES['mets']
TAG_METS_FPTR             = '{%s}fptr' % NAMESPACES['mets']
TAG_METS_FLOCAT           = '{%s}FLocat' % NAMESPACES['mets']
TAG_METS_METSHDR          = '{%s}metsHdr' % NAMESPACES['mets']
TAG_METS_NAME             = '{%s}name' % NAMESPACES['mets']
TAG_METS_STRUCTMAP        = '{%s}structMap' % NAMESPACES['mets']

TAG_MODS_IDENTIFIER       = '{%s}identifier' % NAMESPACES['mods']

TAG_PAGE_COORDS           = '{%s}Coords' % NAMESPACES['page']
TAG_PAGE_READINGORDER     = '{%s}ReadingOrder' % NAMESPACES['page']
TAG_PAGE_REGIONREFINDEXED = '{%s}RegionRefIndexed' % NAMESPACES['page']
TAG_PAGE_TEXTLINE         = '{%s}TextLine' % NAMESPACES['page']
TAG_PAGE_TEXTEQUIV        = '{%s}TextEquiv' % NAMESPACES['page']
TAG_PAGE_TEXTREGION       = '{%s}TextRegion' % NAMESPACES['page']
