import logging
import zipfile
import shutil
import os
import subprocess

logger = logging.getLogger("mandatemind-agent")


class UpdateManager:
    def __init__(self, install_path: str):
        self.install_path = install_path

    def apply_update(self, update_zip_path: str):
        logger.info(f"UpdateManager: applying update from {update_zip_path}")

        try:
            extract_dir = "/tmp/mandatemind_agent_update_extract"
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)

            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(update_zip_path, "r") as z:
                z.extractall(extract_dir)

            # Replace agent files
            for root, dirs, files in os.walk(extract_dir):
                rel_path = os.path.relpath(root, extract_dir)
                target_dir = os.path.join(self.install_path, rel_path)

                os.makedirs(target_dir, exist_ok=True)

                for file in files:
                    src = os.path.join(root, file)
                    dst = os.path.join(target_dir, file)
                    shutil.copy2(src, dst)

            logger.info("UpdateManager: update applied successfully")

            # Restart agent
            self.restart_agent()

        except Exception as e:
            logger.error(f"UpdateManager: update failed: {e}")

    def restart_agent(self):
        logger.info("UpdateManager: restarting agent")
        subprocess.Popen(["systemctl", "restart", "mandatemind-agent"])
