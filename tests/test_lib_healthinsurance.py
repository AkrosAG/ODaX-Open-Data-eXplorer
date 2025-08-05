import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from imping.healthinsurance.lib_healthinsurance import (
    LoadData,
    GetRegion,
    GetMunicipalities_MultipleFeeRegions,
    GetMunicipalities_PerCanton,
    GetKantonRegionFromGemeinde,
    GetFeesByParameters,
    GetAlterunterGruppenProVersicherer,
    GetKVNameFromBAGNumber
)


class TestLoadData:
    @patch('pandas.read_csv')
    def test_successful_load(self, mock_read_csv):
        # Arrange
        mock_df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        mock_read_csv.return_value = mock_df
        
        # Act
        result = LoadData('dummy_path.csv')
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        mock_read_csv.assert_called_once_with('dummy_path.csv', sep=';', encoding='latin1')
    
    @patch('pandas.read_csv', side_effect=FileNotFoundError)
    def test_file_not_found(self, mock_read_csv):
        # Act
        result = LoadData('nonexistent_file.csv')
        
        # Assert
        assert result is None
        mock_read_csv.assert_called_once()
    
    @patch('pandas.read_csv', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid'))
    def test_encoding_error(self, mock_read_csv):
        # Act
        result = LoadData('invalid_encoding.csv')
        
        # Assert
        assert result is None
        mock_read_csv.assert_called_once()
    
    @patch('pandas.read_csv', side_effect=pd.errors.ParserError)
    def test_parser_error(self, mock_read_csv):
        # Act
        result = LoadData('invalid_format.csv')
        
        # Assert
        assert result is None
        mock_read_csv.assert_called_once()
    
    @patch('pandas.read_csv', side_effect=Exception('Unexpected error'))
    def test_unexpected_error(self, mock_read_csv):
        # Act
        result = LoadData('error_file.csv')
        
        # Assert
        assert result is None
        mock_read_csv.assert_called_once()


class TestGetRegion:
    def test_successful_get_region(self):
        # Arrange
        test_data = pd.DataFrame({
            'Kanton': ['ZH', 'ZH', 'BE', 'ZH'],
            'Region': ['Region1', 'Region2', 'Region3', 'Region1']
        })
        
        # Act
        result = GetRegion(test_data, 'ZH')
        
        # Assert
        assert result is not None
        assert isinstance(result, list)
        assert set(result) == {'Region1', 'Region2'}
    
    def test_no_regions_found(self):
        # Arrange
        test_data = pd.DataFrame({
            'Kanton': ['ZH', 'ZH', 'BE'],
            'Region': ['Region1', 'Region2', 'Region3']
        })
        
        # Act
        result = GetRegion(test_data, 'SG')
        
        # Assert
        assert result is None
    
    def test_missing_columns(self):
        # Arrange
        test_data = pd.DataFrame({
            'Canton': ['ZH', 'BE'],  # Wrong column name
            'Area': ['Region1', 'Region3']  # Wrong column name
        })
        
        # Act
        result = GetRegion(test_data, 'ZH')
        
        # Assert
        assert result is None


class TestGetMunicipalities_MultipleFeeRegions:
    @patch('pandas.read_excel')
    def test_successful_get_municipalities(self, mock_read_excel):
        # Arrange
        mock_df = pd.DataFrame({
            'Kanton': ['ZH', 'ZH', 'BE', 'ZH'],
            'Region': [1, 2, 1, 1],
            'Gemeinde': ['Zurich', 'Winterthur', 'Bern', 'Uster']
        })
        mock_read_excel.return_value = mock_df
        
        # Act
        result = GetMunicipalities_MultipleFeeRegions('dummy_path.xlsx', 'ZH', 'Region1')
        
        # Assert
        assert result is not None
        assert isinstance(result, list)
        assert set(result) == {'Zurich', 'Uster'}
        mock_read_excel.assert_called_once_with('dummy_path.xlsx', sheet_name='Anhang EDI Ver. über die PR')
    
    @patch('pandas.read_excel', side_effect=FileNotFoundError)
    def test_file_not_found(self, mock_read_excel):
        # Act
        result = GetMunicipalities_MultipleFeeRegions('nonexistent_file.xlsx', 'ZH', 'Region1')
        
        # Assert
        assert result is None
        mock_read_excel.assert_called_once()
    
    @patch('pandas.read_excel', side_effect=Exception('Unexpected error'))
    def test_unexpected_error(self, mock_read_excel):
        # Act
        result = GetMunicipalities_MultipleFeeRegions('error_file.xlsx', 'ZH', 'Region1')
        
        # Assert
        assert result is None
        mock_read_excel.assert_called_once()


class TestGetMunicipalities_PerCanton:
    @patch('requests.get')
    def test_successful_get_municipalities_per_canton(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.content = """Name,Canton
Zurich,ZH
Winterthur,ZH
Bern,BE
Uster,ZH""".encode('utf-8')
        mock_get.return_value = mock_response
        
        # Act
        result = GetMunicipalities_PerCanton('ZH')
        
        # Assert
        assert result is not None
        assert isinstance(result, list)
        assert set(result) == {'Zurich', 'Winterthur', 'Uster'}
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_json_response(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = """Name,Canton
Zurich,ZH
Winterthur,ZH
Bern,BE
Uster,ZH"""
        mock_get.return_value = mock_response
        
        # Act
        result = GetMunicipalities_PerCanton('ZH')
        
        # Assert
        assert result is not None
        assert isinstance(result, list)
        assert set(result) == {'Zurich', 'Winterthur', 'Uster'}
        mock_get.assert_called_once()


class TestGetKantonRegionFromGemeinde:
    @patch('pandas.read_excel')
    def test_successful_get_kanton_region(self, mock_read_excel):
        # Arrange
        mock_df = pd.DataFrame({
            'Gemeinde': ['Zurich', 'Winterthur', 'Bern'],
            'Kanton': ['ZH', 'ZH', 'BE'],
            'Region': [1, 2, 3]
        })
        mock_read_excel.return_value = mock_df
        
        # Act
        result = GetKantonRegionFromGemeinde('dummy_path.xlsx', 'Zurich')
        
        # Assert
        assert result is not None
        assert isinstance(result, tuple)
        assert result == ('ZH', '1')
        mock_read_excel.assert_called_once_with('dummy_path.xlsx', sheet_name='Anhang EDI Ver. über die PR')
    
    @patch('pandas.read_excel')
    def test_case_insensitive_gemeinde_match(self, mock_read_excel):
        # Arrange
        mock_df = pd.DataFrame({
            'Gemeinde': ['Zurich', 'Winterthur', 'Bern'],
            'Kanton': ['ZH', 'ZH', 'BE'],
            'Region': [1, 2, 3]
        })
        mock_read_excel.return_value = mock_df
        
        # Act
        result = GetKantonRegionFromGemeinde('dummy_path.xlsx', 'zurich')  # lowercase
        
        # Assert
        assert result is not None
        assert result == ('ZH', '1')
    
    @patch('pandas.read_excel')
    def test_gemeinde_not_found(self, mock_read_excel):
        # Arrange
        mock_df = pd.DataFrame({
            'Gemeinde': ['Zurich', 'Winterthur', 'Bern'],
            'Kanton': ['ZH', 'ZH', 'BE'],
            'Region': [1, 2, 3]
        })
        mock_read_excel.return_value = mock_df
        
        # Act
        result = GetKantonRegionFromGemeinde('dummy_path.xlsx', 'Geneva')
        
        # Assert
        assert result is None
    
    @patch('pandas.read_excel', side_effect=FileNotFoundError)
    def test_file_not_found(self, mock_read_excel):
        # Act
        result = GetKantonRegionFromGemeinde('nonexistent_file.xlsx', 'Zurich')
        
        # Assert
        assert result is None
        mock_read_excel.assert_called_once()


class TestGetFeesByParameters:
    def test_successful_get_fees(self):
        # Arrange
        test_data = pd.DataFrame({
            'Kanton': ['ZH', 'ZH', 'BE', 'ZH'],
            'Region': ['Region1', 'Region1', 'Region3', 'Region2'],
            'Unfalleinschluss': ['Ja', 'Nein', 'Ja', 'Ja'],
            'Altersklasse': ['AKL-ERW', 'AKL-ERW', 'AKL-ERW', 'AKL-KIN'],
            'Franchise': [300, 500, 300, 300],
            'Tariftyp': ['Standard', 'Standard', 'Standard', 'Standard'],
            'Altersuntergruppe': ['', '', '', '0-18'],
            'Praemie': [400, 350, 420, 100]
        })
        
        # Act
        result = GetFeesByParameters(
            test_data, 'ZH', 'Region1', 'AKL-ERW', 'Ja', 300, 'Standard'
        )
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]['Praemie'] == 400
    
    def test_get_fees_with_altersgruppe(self):
        # Arrange
        test_data = pd.DataFrame({
            'Kanton': ['ZH', 'ZH', 'ZH'],
            'Region': ['Region1', 'Region1', 'Region1'],
            'Unfalleinschluss': ['Ja', 'Ja', 'Ja'],
            'Altersklasse': ['AKL-KIN', 'AKL-KIN', 'AKL-KIN'],
            'Franchise': [300, 300, 300],
            'Tariftyp': ['Standard', 'Standard', 'Standard'],
            'Altersuntergruppe': ['0-18', '19-25', '0-18'],
            'Praemie': [100, 150, 110]
        })
        
        # Act
        result = GetFeesByParameters(
            test_data, 'ZH', 'Region1', 'AKL-KIN', 'Ja', 300, 'Standard', '0-18'
        )
        
        # Assert
        assert result is not None
        assert len(result) == 2
        assert all(result['Altersuntergruppe'] == '0-18')
    
    def test_missing_columns(self):
        # Arrange
        test_data = pd.DataFrame({
            'Kanton': ['ZH', 'BE'],
            # Missing required columns
        })
        
        # Act & Assert
        with pytest.raises(ValueError):
            GetFeesByParameters(
                test_data, 'ZH', 'Region1', 'AKL-ERW', 'Ja', 300, 'Standard'
            )


class TestGetAlterunterGruppenProVersicherer:
    def test_successful_get_altersuntergruppen(self):
        # Arrange
        test_data = pd.DataFrame({
            'Kanton': ['ZH', 'ZH', 'ZH', 'ZH'],
            'Region': ['Region1', 'Region1', 'Region1', 'Region1'],
            'Unfalleinschluss': ['Ja', 'Ja', 'Ja', 'Ja'],
            'Altersklasse': ['AKL-KIN', 'AKL-KIN', 'AKL-KIN', 'AKL-KIN'],
            'Franchise': [300, 300, 300, 300],
            'Tariftyp': ['Standard', 'Standard', 'Standard', 'Standard'],
            'Versicherer': [123, 123, 456, 456],
            'Altersuntergruppe': ['0-18', '19-25', '0-18', '19-25']
        })
        
        # Act
        result = GetAlterunterGruppenProVersicherer(
            test_data, 'ZH', 'Region1', 'AKL-KIN', 'Ja', 300, 'Standard'
        )
        
        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert len(result) == 2
        assert result[123] == ['0-18', '19-25']
        assert result[456] == ['0-18', '19-25']
    
    def test_missing_columns(self):
        # Arrange
        test_data = pd.DataFrame({
            'Kanton': ['ZH', 'BE'],
            # Missing required columns
        })
        
        # Act & Assert
        with pytest.raises(ValueError):
            GetAlterunterGruppenProVersicherer(
                test_data, 'ZH', 'Region1', 'AKL-KIN', 'Ja', 300, 'Standard'
            )


class TestGetKVNameFromBAGNumber:
    @patch('pandas.read_excel')
    def test_successful_get_kv_name(self, mock_read_excel):
        # Arrange
        mock_df = pd.DataFrame({
            'Nummer': [123, 456, 789],
            'Name': ['Insurer A', 'Insurer B', 'Insurer C']
        })
        mock_read_excel.return_value = mock_df
        
        # Act
        result = GetKVNameFromBAGNumber(123, 'dummy_path.xlsx')
        
        # Assert
        assert result is not None
        assert result == 'Insurer A'
        mock_read_excel.assert_called_once()
    
    @patch('pandas.read_excel')
    def test_bag_number_not_found(self, mock_read_excel):
        # Arrange
        mock_df = pd.DataFrame({
            'Nummer': [123, 456, 789],
            'Name': ['Insurer A', 'Insurer B', 'Insurer C']
        })
        mock_read_excel.return_value = mock_df
        
        # Act
        result = GetKVNameFromBAGNumber(999, 'dummy_path.xlsx')
        
        # Assert
        assert result is None
    
    @patch('pandas.read_excel', side_effect=[ValueError, pd.DataFrame({
        'Nummer': [123, 456],
        'Name': ['Insurer A', 'Insurer B']
    })])
    def test_try_alternative_sheet(self, mock_read_excel):
        # Act
        result = GetKVNameFromBAGNumber(123, 'dummy_path.xlsx')
        
        # Assert
        assert result is not None
        assert result == 'Insurer A'
        assert mock_read_excel.call_count == 2
    
    @patch('pandas.read_excel', side_effect=Exception('Unexpected error'))
    def test_unexpected_error(self, mock_read_excel):
        # Act
        result = GetKVNameFromBAGNumber(123, 'error_file.xlsx')
        
        # Assert
        assert result is None
        mock_read_excel.assert_called_once()