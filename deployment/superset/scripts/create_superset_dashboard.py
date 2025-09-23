#!/usr/bin/env python3
"""
Script to create pollution map dashboard in Superset
"""

import requests
import json
import time
import sys
from typing import Dict, Any

class SupersetClient:
    def __init__(self, base_url: str = "http://localhost:8088"):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
        
    def login(self, username: str = "admin", password: str = "password") -> bool:
        """Login to Superset and get CSRF token"""
        # Get CSRF token
        response = self.session.get(f"{self.base_url}/login/")
        if response.status_code == 200:
            # Extract CSRF token from response
            import re
            csrf_match = re.search(r'csrf_token.*?value="([^"]*)"', response.text)
            if csrf_match:
                self.csrf_token = csrf_match.group(1)
        
        # Login
        login_data = {
            "username": username,
            "password": password,
            "csrf_token": self.csrf_token
        }
        
        response = self.session.post(f"{self.base_url}/login/", data=login_data)
        return response.status_code == 200
    
    def create_dataset(self, dataset_config: Dict[str, Any]) -> int:
        """Create a dataset in Superset"""
        headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": self.csrf_token,
            "Referer": self.base_url
        }
        print(self.base_url)
        response = self.session.post(
            f"{self.base_url}/api/v1/dataset/",
            headers=headers,
            json=dataset_config
        )
        
        if response.status_code == 201:
            return response.json()["id"]
        else:
            print(f"Failed to create dataset: {response.text}")
            return None
    
    def create_chart(self, chart_config: Dict[str, Any]) -> int:
        """Create a chart in Superset"""
        headers = {
            "Content-Type": "application/json", 
            "X-CSRFToken": self.csrf_token,
            "Referer": self.base_url
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/chart/",
            headers=headers,
            json=chart_config
        )
        
        if response.status_code == 201:
            return response.json()["id"]
        else:
            print(f"Failed to create chart: {response.text}")
            return None
    
    def create_dashboard(self, dashboard_config: Dict[str, Any]) -> int:
        """Create a dashboard in Superset"""
        headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": self.csrf_token, 
            "Referer": self.base_url
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/dashboard/",
            headers=headers,
            json=dashboard_config
        )
        
        if response.status_code == 201:
            return response.json()["id"]
        else:
            print(f"Failed to create dashboard: {response.text}")
            return None

def create_plotting_dataset(client: SupersetClient, database_id: int) -> int:
    """Create pollution dataset"""
    dataset_config = {
        "database": database_id,
        "table_name": "test4",
        "sql": """
        SELECT 
            lv95_easting,
            lv95_northing,
            short_code
        FROM airq.stations
        """

    }
    return client.create_dataset(dataset_config)

def create_plotting_charts(client: SupersetClient, dataset_id: int) -> list:
    """Create pollution visualization charts"""
    chart_ids = []
    
    # 1. Pollution Map (Scatter plot on map)
    map_chart = {
        "slice_name": "Pollution Levels Map",
        "viz_type": "deck_scatter",
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps({
            "longitude": "longitude",
            "latitude": "latitude",
            "color": "black",
            "point_radius_fixed": {"type": "fix", "value": 1000},
            "point_radius_unit": "meters",
            "color_scheme": "d3Category20c",
            "viewport": {
                "longitude": -95.7129,
                "latitude": 37.0902,
                "zoom": 3.5,
                "bearing": 0,
                "pitch": 0
            },
            "mapbox_style": "mapbox://styles/mapbox/light-v9",
            "row_limit": 10000
        })
    }
    chart_ids.append(client.create_chart(map_chart))
    
    # 2. Pollution Heatmap
    heatmap_chart = {
        "slice_name": "Pollution Heatmap",
        "viz_type": "deck_hex",
        "datasource_id": dataset_id,
        "datasource_type": "table", 
        "params": json.dumps({
            "longitude": "lv95_easting",
            "latitude": "lv95_northing",
            "grid_size": 40,
            "color_scheme": "rdYlBu_r",
            "viewport": {
                "longitude": -95.7129,
                "latitude": 37.0902, 
                "zoom": 3.5,
                "bearing": 0,
                "pitch": 0
            },
            "mapbox_style": "mapbox://styles/mapbox/light-v9"
        })
    }
    chart_ids.append(client.create_chart(heatmap_chart))
    
    # 3. Pollution by Region Bar Chart
    bar_chart = {
        "slice_name": "Average Pollution by Region",
        "viz_type": "dist_bar",
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps({
            "metrics": ["avg(pollution_level)"],
            "groupby": ["region"],
            "color_scheme": "bnbColors",
            "show_legend": True,
            "rich_tooltip": True,
            "show_bar_value": True,
            "y_axis_format": ".1f",
            "y_axis_label": "Average Pollution Level"
        })
    }
    chart_ids.append(client.create_chart(bar_chart))
    
    # 4. Pollution Trend Line Chart
    line_chart = {
        "slice_name": "Pollution Trend Over Time",
        "viz_type": "line",
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps({
            "metrics": ["avg(pollution_level)"],
            "granularity_sqla": "measurement_date",
            "time_grain_sqla": "P1D",
            "color_scheme": "bnbColors",
            "show_legend": True,
            "rich_tooltip": True,
            "show_markers": True,
            "y_axis_format": ".1f",
            "y_axis_label": "Average Pollution Level"
        })
    }
    chart_ids.append(client.create_chart(line_chart))
    
    return chart_ids

def create_pollution_dashboard(client: SupersetClient, chart_ids: list) -> int:
    """Create pollution dashboard with charts"""
    dashboard_config = {
        "dashboard_title": "Airquality Monitoring Dashboard",
        "slug": "Airquality-monitoring",
        "published": True,
        "json_metadata": json.dumps({
            "color_scheme": "supersetColors",
            "refresh_frequency": 0,
            "timed_refresh_immune_slices": [],
            "expanded_slices": {},
            "label_colors": {},
            "color_scheme_domain": [],
            "cross_filters_enabled": True
        }),
        "position_json": json.dumps({
            "CHART-1": {
                "children": [],
                "id": "CHART-1", 
                "meta": {"chartId": chart_ids[0], "height": 70, "sliceName": "Pollution Levels Map", "width": 8},
                "type": "CHART"
            },
            "CHART-2": {
                "children": [],
                "id": "CHART-2",
                "meta": {"chartId": chart_ids[1], "height": 70, "sliceName": "Pollution Heatmap", "width": 4}, 
                "type": "CHART"
            },
            "CHART-3": {
                "children": [],
                "id": "CHART-3",
                "meta": {"chartId": chart_ids[2], "height": 50, "sliceName": "Average Pollution by Region", "width": 6},
                "type": "CHART"
            },
            "CHART-4": {
                "children": [],
                "id": "CHART-4",
                "meta": {"chartId": chart_ids[3], "height": 50, "sliceName": "Pollution Trend Over Time", "width": 6},
                "type": "CHART"
            },
            "DASHBOARD_VERSION_KEY": "v2",
            "GRID_ID": {
                "children": ["ROW-1", "ROW-2"],
                "id": "GRID_ID",
                "type": "GRID"
            },
            "ROW-1": {
                "children": ["CHART-1", "CHART-2"],
                "id": "ROW-1",
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
                "type": "ROW"
            },
            "ROW-2": {
                "children": ["CHART-3", "CHART-4"],
                "id": "ROW-2", 
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
                "type": "ROW"
            }
        })
    }
    
    return client.create_dashboard(dashboard_config)

def main():
    """Main function to create pollution monitoring dashboard"""
    print("Creating Pollution Monitoring Dashboard in Superset...")

    # Initialize client
    client = SupersetClient()
    
    # Login
    print("Logging in to Superset...")
    if not client.login():
        print("Failed to login to Superset")
        sys.exit(1)
    
    print("Login successful!")
    
    # Assume Trino database ID is 1 (adjust as needed)
    database_id = 1
    #database_id = "postgres_db"
    # Create dataset
    print("Creating pollution dataset...")


    dataset_id = create_plotting_dataset(client, database_id)
    if not dataset_id:
        print("Failed to create dataset")
        sys.exit(1)
    
    print(f"Dataset created with ID: {dataset_id}")
    
    # Create charts
    print("Creating pollution charts...")
    chart_ids = create_plotting_charts(client, dataset_id)
    if not all(chart_ids):
        print("Failed to create some charts")
        sys.exit(1)
    
    print(f"Charts created with IDs: {chart_ids}")
    
    # Create dashboard
    print("Creating pollution dashboard...")
    dashboard_id = create_pollution_dashboard(client, chart_ids)
    if not dashboard_id:
        print("Failed to create dashboard")
        sys.exit(1)
    
    print(f"Dashboard created with ID: {dashboard_id}")
    print(f"Access your dashboard at: http://localhost:8088/superset/dashboard/{dashboard_id}/")
    print("Dashboard creation completed successfully!")

if __name__ == "__main__":
    main()

