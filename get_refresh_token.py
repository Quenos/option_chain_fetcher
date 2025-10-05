"""
Script to obtain and store Tastytrade OAuth credentials.

This script helps you generate a refresh token for Tastytrade API access
and securely stores it along with your client ID and client secret in a .secrets file.

Usage:
    python get_refresh_token.py
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from tastytrade.oauth import login

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_refresh_token() -> Optional[str]:
    """
    Launch the OAuth login flow to get a refresh token.
    
    This will open a browser window where you'll need to:
    1. Paste your OAuth application's Client ID
    2. Paste your OAuth application's Client Secret
    3. Log in to your Tastytrade account
    4. Authorize the application
        
    Returns:
        The refresh token string, or None if login failed.
    """
    logger.info("Starting OAuth login flow...")
    logger.info("A browser window will open. Follow the instructions to authorize your application.")
    
    try:
        refresh_token = login(is_test=False)
        if refresh_token:
            logger.info("Successfully obtained refresh token!")
            return refresh_token
        else:
            logger.error("Failed to obtain refresh token")
            return None
    except Exception as e:
        logger.error(f"Error during OAuth login: {str(e)}")
        return None


def save_credentials_to_file(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    file_path: str = ".secrets"
) -> bool:
    """
    Save OAuth credentials to a .secrets file.
    
    Args:
        client_id: OAuth application client ID
        client_secret: OAuth application client secret
        refresh_token: OAuth refresh token
        file_path: Path to save the credentials file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        secrets_path = Path(file_path)
        
        # Check if file already exists
        if secrets_path.exists():
            logger.warning(f"{file_path} already exists. Creating backup...")
            backup_path = Path(f"{file_path}.backup")
            secrets_path.rename(backup_path)
            logger.info(f"Backup created at {backup_path}")
        
        # Write credentials to file
        with open(secrets_path, 'w') as f:
            f.write("# Tastytrade OAuth Credentials\n")
            f.write("# DO NOT COMMIT THIS FILE TO VERSION CONTROL\n")
            f.write("# Keep this file secure and private\n\n")
            f.write(f"TT_API_CLIENT_ID={client_id}\n")
            f.write(f"TT_API_CLIENT_SECRET={client_secret}\n")
            f.write(f"TT_REFRESH_TOKEN={refresh_token}\n")
        
        # Set file permissions to be readable/writable only by owner
        os.chmod(secrets_path, 0o600)
        
        logger.info(f"Credentials successfully saved to {file_path}")
        logger.info(f"File permissions set to 600 (owner read/write only)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving credentials to file: {str(e)}")
        return False


def update_gitignore() -> None:
    """
    Ensure .secrets file is in .gitignore to prevent accidental commits.
    """
    gitignore_path = Path(".gitignore")
    secrets_entry = ".secrets"
    
    try:
        # Read existing .gitignore if it exists
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                content = f.read()
                
            # Check if .secrets is already in .gitignore
            if secrets_entry in content:
                logger.info(".secrets already in .gitignore")
                return
        else:
            content = ""
        
        # Add .secrets to .gitignore
        with open(gitignore_path, 'a') as f:
            if content and not content.endswith('\n'):
                f.write('\n')
            f.write(f"\n# Tastytrade OAuth credentials\n{secrets_entry}\n{secrets_entry}.backup\n")
        
        logger.info(f"Added {secrets_entry} to .gitignore")
        
    except Exception as e:
        logger.warning(f"Could not update .gitignore: {str(e)}")


def prompt_for_credentials() -> tuple[str, str]:
    """
    Prompt user to enter client ID and secret manually.
    
    Returns:
        Tuple of (client_id, client_secret)
    """
    print("\n" + "="*70)
    print("TASTYTRADE OAUTH APPLICATION CREDENTIALS")
    print("="*70)
    print("\nTo get your Client ID and Client Secret:")
    print("1. Log in to Tastytrade web platform: https://trade.tastytrade.com/")
    print("2. Navigate to: Manage → My Profile → API")
    print("3. Click 'Open API Access' → 'Opt in' (if not already enabled)")
    print("4. Click 'Create Grant'")
    print("5. Select 'Read' permission (minimum)")
    print("6. Set Redirect URI to: http://localhost:8000")
    print("7. Copy the Client ID and Client Secret shown")
    print("\n⚠️  IMPORTANT: Client Secret is shown only ONCE - save it now!")
    print("\nFor detailed instructions, see: OAUTH_SETUP_TUTORIAL.md\n")
    print("="*70 + "\n")
    
    client_id = input("Enter your OAuth Client ID: ").strip()
    client_secret = input("Enter your OAuth Client Secret: ").strip()
    
    return client_id, client_secret


def main() -> int:
    """
    Main function to orchestrate the token generation and storage process.
    
    Returns:
        0 on success, 1 on failure
    """
    logger.info("="*70)
    logger.info("TASTYTRADE REFRESH TOKEN GENERATOR")
    logger.info("="*70)
    logger.info("")
    
    # Get refresh token through OAuth flow
    refresh_token = get_refresh_token()
    
    if not refresh_token:
        logger.error("Failed to obtain refresh token. Exiting.")
        return 1
    
    # Prompt for client credentials
    client_id, client_secret = prompt_for_credentials()
    
    if not client_id or not client_secret:
        logger.error("Client ID and Client Secret are required. Exiting.")
        return 1
    
    # Save credentials to .secrets file
    success = save_credentials_to_file(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        file_path=".secrets"
    )
    
    if not success:
        logger.error("Failed to save credentials. Exiting.")
        return 1
    
    # Update .gitignore to protect the secrets file
    update_gitignore()
    
    logger.info("")
    logger.info("="*70)
    logger.info("SUCCESS!")
    logger.info("="*70)
    logger.info("Your OAuth credentials have been saved to .secrets")
    logger.info("You can now use these credentials in your application.")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Update your application to read from .secrets file")
    logger.info("2. Keep the .secrets file secure and never commit it to git")
    logger.info("3. The refresh token never expires, so you only need to do this once")
    logger.info("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
