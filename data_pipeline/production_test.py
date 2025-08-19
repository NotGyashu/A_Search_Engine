#!/usr/bin/env python3
"""
Production Test Coordinator - Safe Cleanup Version

Runs the C++ crawler and the Python data pipeline simultaneously to simulate
production-like behavior with guaranteed data integrity.

This script:
1.  Starts the data pipeline in continuous monitoring mode.
2.  Starts the crawler, which runs for a fixed duration.
3.  Listens for "PROCESSED_FILE" signals from the pipeline's logs.
4.  Deletes raw data files ONLY after the pipeline has confirmed their processing.
5.  Ensures a graceful shutdown of both processes after the test is complete.
"""

import os
import signal
import subprocess
import time
import threading
import logging
from pathlib import Path
from typing import Optional, Set
import shutil

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("production_test.log", mode='w')
    ]
)
logger = logging.getLogger("ProdTestCoordinator")


class ProductionTestCoordinator:
    """Coordinates the crawler and data pipeline for production-like testing."""

    def __init__(self, crawler_duration_seconds: int = 150):
        self.project_root = Path(__file__).parent.parent
        self.crawler_dir = self.project_root / "crawler"
        self.data_pipeline_dir = self.project_root / "data_pipeline"
        self.raw_data_dir = self.project_root / "RawHTMLdata"

        # Process handles
        self.crawler_process: Optional[subprocess.Popen] = None
        self.pipeline_process: Optional[subprocess.Popen] = None

        # Thread-safe control flags and monitoring sets
        self.shutdown_event = threading.Event()
        self.crawler_finished_event = threading.Event()
        
        self.processed_files: Set[Path] = set()
        self.processed_files_lock = threading.Lock()

        # Test parameters
        self.crawler_duration = crawler_duration_seconds
        self.pipeline_check_interval = 5

    def setup_environment(self):
        """Cleans and sets up the environment for a fresh test run."""
        logger.info("🔧 Setting up environment and cleaning previous run...")
        if self.raw_data_dir.exists():
            shutil.rmtree(self.raw_data_dir)
        self.raw_data_dir.mkdir(exist_ok=True)
        
        os.environ.update({
            "CHECK_INTERVAL_SECONDS": str(self.pipeline_check_interval),
            "MAX_WORKERS": "2",
            "BATCH_SIZE": "500",    
        })
        logger.info("✅ Environment setup complete.")

    def start_process(self, command: list, cwd: Path, name: str) -> Optional[subprocess.Popen]:
        """Starts a subprocess and returns its handle."""
        logger.info(f"🚀 Starting {name}...")
        try:
            process = subprocess.Popen(
                command, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, preexec_fn=os.setsid
            )
            logger.info(f"✅ {name} started (PID: {process.pid})")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to start {name}: {e}")
            return None

    def _log_subprocess_output(self, process: subprocess.Popen, name: str):
        """Reads and logs the output of a subprocess, listening for signals."""
        while process.poll() is None and not self.shutdown_event.is_set():
            line = process.stdout.readline().strip()
            if not line:
                continue
                
            logger.info(f"[{name}]: {line}")
            
            # Listen for the "PROCESSED_FILE" signal from the pipeline
            if name == "PIPELINE" and line.startswith("PROCESSED_FILE:"):
                try:
                    file_path_str = line.split(":", 1)[1].strip()
                    file_path = Path(file_path_str)
                    if file_path.exists():
                        with self.processed_files_lock:
                            self.processed_files.add(file_path)
                        logger.info(f"🔑 Marked for deletion: {file_path.name}")
                    else:
                        logger.warning(f"⚠️ Processed file not found: {file_path.name}")
                except (IndexError, ValueError) as e:
                    logger.warning(f"⚠️ Could not parse PROCESSED_FILE signal: {e} - {line}")

    def monitor_crawler_runtime(self):
        """Monitors the crawler and terminates it after the specified duration."""
        logger.info(f"👁️ Monitoring crawler runtime ({self.crawler_duration}s)...")
        self.shutdown_event.wait(self.crawler_duration)

        if not self.shutdown_event.is_set():
            logger.info("⏰ Crawler time limit reached, terminating...")
            if self.crawler_process and self.crawler_process.poll() is None:
                self.terminate_process(self.crawler_process, "Crawler")
        
        self.crawler_finished_event.set()
        logger.info("🏁 Crawler phase complete.")

    def monitor_and_cleanup_files(self):
        """Monitors for files and safely cleans them up after they are processed."""
        logger.info("📁 Starting safe file cleanup task...")
        
        while not self.shutdown_event.is_set():
            # Check for files in the raw data directory
            current_files = set()
            if self.raw_data_dir.exists():
                current_files = set(self.raw_data_dir.glob("*.json"))
            
            # Identify files ready for deletion
            with self.processed_files_lock:
                to_delete = self.processed_files.intersection(current_files)
            
            # Delete processed files
            if to_delete:
                logger.info(f"🗑️ Deleting {len(to_delete)} processed files...")
                for file_path in to_delete:
                    try:
                        file_path.unlink()
                        logger.info(f"   - Deleted: {file_path.name}")
                        self.processed_files.remove(file_path)
                    except FileNotFoundError:
                        logger.debug(f"File already deleted: {file_path.name}")
                        self.processed_files.discard(file_path)
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to delete {file_path.name}: {e}")
            
            # Check termination conditions
            if self.shutdown_event.is_set() and not current_files:
                break
                
            time.sleep(self.pipeline_check_interval)

        logger.info("✅ File monitoring and cleanup complete.")

    def wait_for_completion(self):
        """Waits for the crawler to finish and the pipeline to process all files."""
        logger.info("⏳ Waiting for crawler and pipeline to complete...")
        self.crawler_finished_event.wait()
        
        # After crawler is done, wait until the RawHTMLdata directory is empty
        logger.info("⏳ Waiting for all files to be processed...")
        while not self.shutdown_event.is_set():
            if not any(self.raw_data_dir.iterdir()):
                logger.info("✅ All raw HTML files have been processed and deleted.")
                break
            logger.info(f"...remaining files: {len(list(self.raw_data_dir.iterdir()))}")
            time.sleep(self.pipeline_check_interval)
        
        # Allow final processing to complete
        if not self.shutdown_event.is_set():
            logger.info("...giving pipeline 10 extra seconds to finalize...")
            time.sleep(10)

    def terminate_process(self, process: subprocess.Popen, name: str):
        """Terminates a single process gracefully, then forcefully."""
        if process and process.poll() is None:
            logger.info(f"🛑 Terminating {name} (PID: {process.pid})...")
            try:
                # Try graceful termination first
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                logger.warning(f"⚠️ {name} did not terminate gracefully. Forcing exit...")
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Process already terminated

    def shutdown(self):
        """Shuts down all managed processes and threads."""
        if self.shutdown_event.is_set():
            return  # Already shutting down
            
        logger.info("🛑 Initiating graceful shutdown...")
        self.shutdown_event.set()
        
        # Terminate processes
        self.terminate_process(self.crawler_process, "Crawler")
        self.terminate_process(self.pipeline_process, "Pipeline")
        
        logger.info("✅ All processes have been shut down.")

    def run(self):
        """Runs the complete end-to-end production test."""
        self.setup_environment()
        
        # Build process commands
        crawler_exe = str(self.crawler_dir / "build" / "crawler")
        pipeline_venv = str(self.data_pipeline_dir / "dp-venv" / "bin" / "python")
        pipeline_script = str(self.data_pipeline_dir / "run_pipeline.py")

        # Start pipeline first
        self.pipeline_process = self.start_process(
            [pipeline_venv, pipeline_script, "--mode", "continuous"],
            self.data_pipeline_dir, "PIPELINE"
        )
        if not self.pipeline_process:
            logger.critical("❌ Failed to start pipeline. Aborting test.")
            return

        # Give pipeline time to initialize
        time.sleep(5)

        # Start crawler
        self.crawler_process = self.start_process(
            [crawler_exe, "regular", "--max-runtime", "3"],
            self.crawler_dir, "CRAWLER"
        )
        if not self.crawler_process:
            logger.critical("❌ Failed to start crawler. Aborting test.")
            self.shutdown()
            return
        
        # Set up signal handling
        signal.signal(signal.SIGINT, lambda s, f: self.shutdown())
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())
        
        # Start all monitoring threads
        threads = [
            threading.Thread(target=self._log_subprocess_output, args=(self.pipeline_process, "PIPELINE"), daemon=True),
            threading.Thread(target=self._log_subprocess_output, args=(self.crawler_process, "CRAWLER"), daemon=True),
            threading.Thread(target=self.monitor_crawler_runtime, daemon=True),
            threading.Thread(target=self.monitor_and_cleanup_files, daemon=True)
        ]
        
        for t in threads:
            t.start()

        try:
            self.wait_for_completion()
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        finally:
            self.shutdown()
            logger.info("🏁 Production test finished.")


if __name__ == "__main__":
    coordinator = ProductionTestCoordinator(crawler_duration_seconds=150)
    coordinator.run()