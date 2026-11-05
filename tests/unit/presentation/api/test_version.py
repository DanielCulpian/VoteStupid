"""Keep runtime and API version metadata consistent for release candidates."""
from app import __version__
from app.main import create_app
from app.presentation.api.routes import get_info


def test_api_metadata_uses_the_application_version():
    """Expose the same version in API information and the generated OpenAPI schema."""
    assert get_info()['version'] == __version__
    assert create_app().openapi()['info']['version'] == __version__
