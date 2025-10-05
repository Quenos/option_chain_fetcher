import logging
import os

from dotenv import load_dotenv
from tastytrade import OAuthSession

logger = logging.getLogger(__name__)


class ApplicationSession:
    """
    It provides access to the  session object and reads configuration from a config file.
    """

    def __init__(self) -> None:
        try:
            load_dotenv()

            TT_API_CLIENT_SECRET = os.getenv('TT_API_CLIENT_SECRET')
            TT_REFRESH_TOKEN = os.getenv('TT_REFRESH_TOKEN')
            self._session = OAuthSession(TT_API_CLIENT_SECRET, TT_REFRESH_TOKEN)
            self.initialized = True  # Mark as initialized
        except Exception as e:
            logger.error(f"Error initializing ApplicationSession: {str(e)}")
            raise

    @property
    def session(self) -> OAuthSession:
        """
        Get the  session object.

        Returns:
            Session: The  session object.
        """
        if not hasattr(self, '_session'):
            raise AttributeError("Session not initialized")
        self._session.refresh()
        return self._session
