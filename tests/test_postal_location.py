import pytest
import csv
import tempfile
import os
from pathlib import Path

import sys
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.postal_location_service import PostalLocationService


@pytest.fixture
def mock_csv_path():
    data = [
        ["circlename","regionname","divisionname","officename","pincode","officetype","delivery","district","statename","latitude","longitude"],
        ["Telangana Circle","Hyderabad","Adilabad","Test HO","111111","HO","Delivery","DIST1","STATE1","10.0","20.0"],
        ["Telangana Circle","Hyderabad","Adilabad","Test BO","111111","BO","Delivery","DIST1","STATE1","11.0","21.0"], # Same PIN, lower rank
        ["Telangana Circle","Hyderabad","Adilabad","No Coord BO","222222","BO","Delivery","DIST2","STATE2","",""],
        ["Telangana Circle","Hyderabad","Adilabad","Coord BO","222222","BO","Delivery","DIST2","STATE2","12.0","22.0"], # Same PIN, has coord
        ["Telangana Circle","Hyderabad","Adilabad","Alpha B","333333","BO","Delivery","DIST3","STATE3","13.0","23.0"],
        ["Telangana Circle","Hyderabad","Adilabad","Alpha A","333333","BO","Delivery","DIST3","STATE3","14.0","24.0"], # Alphabetically earlier
        ["Telangana Circle","Hyderabad","Adilabad","Non Del","444444","BO","Non-Delivery","DIST4","STATE4","15.0","25.0"],
        ["Telangana Circle","Hyderabad","Adilabad","Del","444444","BO","Delivery","DIST4","STATE4","16.0","26.0"], # Delivery preferred
        ["Telangana Circle","Hyderabad","Adilabad","Bad Coord","555555","BO","Delivery","DIST5","STATE5","invalid","coords"],
    ]
    
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)
        
    yield Path(path)
    os.remove(path)


class TestPostalLocationService:
    
    def test_valid_pin_resolution(self, mock_csv_path):
        service = PostalLocationService(data_path=mock_csv_path)
        result = service.get_location_for_pin("111111")
        
        assert result is not None
        assert result["pin"] == "111111"
        assert result["district"] == "DIST1"
        assert result["state"] == "STATE1"
        # Determinism: HO > BO
        assert result["officename"] == "Test HO"
        assert result["latitude"] == 10.0
        assert result["longitude"] == 20.0

    def test_unknown_pin(self, mock_csv_path):
        service = PostalLocationService(data_path=mock_csv_path)
        result = service.get_location_for_pin("999999")
        assert result is None

    def test_deterministic_resolution_has_coords(self, mock_csv_path):
        service = PostalLocationService(data_path=mock_csv_path)
        result = service.get_location_for_pin("222222")
        
        # Should prefer "Coord BO" over "No Coord BO"
        assert result["officename"] == "Coord BO"
        assert result["latitude"] == 12.0
        assert result["longitude"] == 22.0

    def test_deterministic_resolution_alphabetical(self, mock_csv_path):
        service = PostalLocationService(data_path=mock_csv_path)
        result = service.get_location_for_pin("333333")
        
        # Should prefer "Alpha A" over "Alpha B" since they are both BO, Delivery, and have coords
        assert result["officename"] == "Alpha A"
        assert result["latitude"] == 14.0

    def test_deterministic_resolution_delivery(self, mock_csv_path):
        service = PostalLocationService(data_path=mock_csv_path)
        result = service.get_location_for_pin("444444")
        
        # Should prefer "Del" over "Non Del"
        assert result["officename"] == "Del"
        assert result["latitude"] == 16.0

    def test_missing_coordinates(self, mock_csv_path):
        service = PostalLocationService(data_path=mock_csv_path)
        result = service.get_location_for_pin("555555")
        
        assert result is not None
        assert result["pin"] == "555555"
        # Invalid coordinates should be treated as missing
        assert result["latitude"] is None
        assert result["longitude"] is None
        assert result["district"] == "DIST5"

