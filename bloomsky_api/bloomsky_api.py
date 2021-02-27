import os
import requests
from datetime import datetime
from dateutil import tz

from .exceptions import APIKeyMissing, APIKeyInvalid, BloomSkyConnection, NoDevicesFound

BLOOMSKY_API_KEY_VARIABLE = 'BLOOMSKY_API_KEY'
DEFAULT_API_URL = 'https://api.bloomsky.com/api/skydata/'


class BloomSkyAPIResponse(object):
    field_mapping = [
            ('ALT', 'altitude'),
            ('CityName', 'city_name'),
            ('DST', 'is_dst'),
            ('DeviceID', 'device_id'),
            ('DeviceName', 'device_name'),
            ('FullAddress', 'full_address'),
            ('LAT', 'latitude'),
            ('LON', 'longitude'),
            ('NumOfFavorites', 'favorites_count'),
            ('NumOfFollowers', 'followers_count'),
            ('RegisterTime', 'registered_timestamp'),
            ('Searchable', 'is_searchable'),
            ('StreetName', 'street_name'),
            ('UTC', 'utc_offset'),
            ('VideoList', 'video_urls'),
            ]
    data_field_mapping = [
            ('DeviceType', 'device_type'),
            ('Humidity', 'humidity'),
            ('ImageTS', 'image_timestamp'),
            ('ImageURL', 'image_url'),
            ('Luminance', 'luminance'),
            ('Night', 'is_night'),
            ('Pressure', 'pressure'),
            ('Rain', 'is_raining'),
            ('TS', 'data_timestamp'),
            ('Temperature', 'temperature'),
            ('UVIndex', 'uv_index'),
            ('Voltage', 'voltage'),
            ]

    def __init__(self, response):
        self._raw_response = response
        self._json = response.json()
        self.data = [self._remap_data(device) for device in self._json]
        self._normalize_data()

    @classmethod
    def _remap_data(cls, response_data):
        remapped_data = {}
        for old_name, new_name in cls.field_mapping:
            remapped_data[new_name] = response_data.get(old_name)
        remapped_data['outdoor'] = {}
        for old_name, new_name in cls.data_field_mapping:
            remapped_data['outdoor'][new_name] = \
                    response_data['Data'].get(old_name)
        indoor = response_data.get('Point', {})
        remapped_data['indoor'] = {
                'humidity': indoor.get('Humidity'),
                'temperature': indoor.get('Temperature'),
                }
        return remapped_data

    def _normalize_data(self):
        for device in self.data:
            device['is_dst'] = bool(device['is_dst'])
            offset_hours = device['utc_offset']
            device['outdoor']['data_timestamp'] = self._timestamp_to_iso_format(
                    device['outdoor']['data_timestamp'], offset_hours)
            device['outdoor']['image_timestamp'] = self._timestamp_to_iso_format(
                    device['outdoor']['image_timestamp'], offset_hours)
            device['outdoor']['uv_index'] = int(device['outdoor']['uv_index'])
            device['registered_timestamp'] = self._timestamp_to_iso_format(
                    device['registered_timestamp'], offset_hours)

    @staticmethod
    def _timestamp_to_iso_format(timestamp, offset_hours=0):
        try:
            pseudo_timezone = tz.tzoffset('Unknown', int(offset_hours * 3600))
            return datetime.fromtimestamp(timestamp, pseudo_timezone).isoformat()
        except:
            raise
            return None

    def __repr__(self):
        return "{0}".format(self._json)


class BloomSkyAPIClient(object):
    """ A client for interacting with the BloomSky API """

    def __init__(self, api_key=None, api_url=None):
        self.api_key = self._get_api_key(api_key)
        self.api_url = self._get_api_url(api_url)

    def request_data(self, intl_units=False):
        if self.api_key is None:
            raise APIKeyMissing('No API key provided. Set via {0} environment'
            ' variable or argument.'.format(BLOOMSKY_API_KEY_VARIABLE))
        headers = {'Authorization': self.api_key}
        params = {}
        if intl_units:
            params['unit'] = 'intl'

        try:
            response = requests.get(self.api_url, headers=headers, params=params)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise BloomSkyConnection("Error connecting to bloomsky")
        except requests.exceptions.HTTPError:
            raise APIKeyInvalid("Invalid API Key")
        if response.status_code == 405:
            raise NoDevicesFound("No bloomsky devices found")

        return BloomSkyAPIResponse(response)

    def get_data(self, intl_units=False):
        response = self.request_data(intl_units=intl_units)

        return response.data

    @staticmethod
    def _get_api_key(provided_api_key=None):
        if provided_api_key is not None:
            return provided_api_key
        return os.environ.get(BLOOMSKY_API_KEY_VARIABLE)
        # TODO: consider looking for key in config file too?

    @staticmethod
    def _get_api_url(provided_api_url=None):
        if provided_api_url is not None:
            return provided_api_url
        else:
            return DEFAULT_API_URL



