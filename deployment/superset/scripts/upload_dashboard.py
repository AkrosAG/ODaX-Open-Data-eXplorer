#!/usr/bin/env python3
"""
Simple script to upload dashboard ZIP file to Superset
"""

import os
import subprocess
import time


def upload_dashboard():
    """Upload dashboard ZIP file to Superset"""
    print("📤 Uploading dashboard ZIP file...")

    # Path to the dashboard ZIP file
    dashboard_zip = "/app/dashboards/dashboard_export_20250803T141554.zip"

    if not os.path.exists(dashboard_zip):
        print(f"❌ Dashboard ZIP file not found: {dashboard_zip}")
        print(
            "💡 You need to export a working dashboard as ZIP and place it in the dashboards folder"
        )
        return False

    try:
        # Use Superset CLI to import the dashboard with username
        result = subprocess.run(
            [
                "superset",
                "import-dashboards",
                "--path",
                dashboard_zip,
                "--username",
                "admin",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            print("✅ Dashboard uploaded successfully!")
            print("🌐 Access your dashboard at: http://localhost:8088")
            return True
        else:
            print(f"❌ Failed to upload dashboard: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("⏰ Timeout uploading dashboard")
        return False
    except Exception as e:
        print(f"❌ Error uploading dashboard: {e}")
        return False


if __name__ == "__main__":
    # Wait a bit for Superset to be ready
    time.sleep(10)
    upload_dashboard()
