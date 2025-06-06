from django.contrib.postgres.search import SearchVector
from django.db.models import F, TextChoices
from django.db.models.fields.json import KeyTextTransform
from django.utils.translation import gettext_lazy as _

# Imported from
# https://github.com/postgres/postgres/blob/REL_14_STABLE/src/bin/initdb/initdb.c#L659
TSEARCH_CONFIG_LANGUAGES = {
    "ar": "arabic",
    "ca": "catalan",
    "da": "danish",
    "de": "german",
    "el": "greek",
    "en": "english",
    "es": "spanish",
    "eu": "basque",
    "fi": "finnish",
    "fr": "french",
    "ga": "irish",
    "hi": "hindi",
    "hu": "hungarian",
    "hy": "armenian",
    "id": "indonesian",
    "it": "italian",
    "lt": "lithuanian",
    "ne": "nepali",
    "nl": "dutch",
    "no": "norwegian",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "sr": "serbian",
    "sv": "swedish",
    "ta": "tamil",
    "tr": "turkish",
    "yi": "yiddish",
}

# Imported from
# https://github.com/postgres/postgres/blob/REL_14_STABLE/src/bin/initdb/initdb.c#L2557
DEFAULT_TEXT_SEARCH_CONFIG = "simple"

DOCUMENT_SEARCH_VECTOR = (
    SearchVector("title", weight="A", config=F("config"))
    + SearchVector(KeyTextTransform("slug", "metadata"), weight="A", config=F("config"))
    + SearchVector(KeyTextTransform("toc", "metadata"), weight="B", config=F("config"))
    + SearchVector(KeyTextTransform("body", "metadata"), weight="C", config=F("config"))
    + SearchVector(
        KeyTextTransform("parents", "metadata"), weight="D", config=F("config")
    )
)

START_SEL = "<mark>"
STOP_SEL = "</mark>"


class DocumentationCategory(TextChoices):
    """
    Categories used to filter the documentation search.
    The value must match a folder name within django/docs.
    """

    # Diátaxis folders.
    REFERENCE = "ref", _("API Reference")
    TOPICS = "topics", _("Using Django")
    HOWTO = "howto", _("How-to guides")
    RELEASE_NOTES = "releases", _("Release notes")

    @classmethod
    def parse(cls, value, default=None):
        try:
            return cls(value)
        except ValueError:
            return None
