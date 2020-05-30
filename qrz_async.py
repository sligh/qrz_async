import requests
from asyncio import gather, run
from aiohttp import ClientSession, TCPConnector
from xml.etree import ElementTree as ET


class QRZ:

    # A python class to query QRZ asynchronously.
    # Justin Sligh, 2020
    
    def __init__(self):
        self.username = 'INSERT'
        self.password = 'INSERT'
        self.base_url = 'http://xmldata.qrz.com/xml/1.31/'
        self.headers = {'Content-Type': 'application/xml', 'Cache-Control': 'no-cache'}
        self.agent = 'qrz_async'
        self.timeout = 10

        self.stations = []

        # Session details
        self.version = ''
        self.session_key = ''
        self.count = ''
        self.expiration = ''

        # Run authentication
        self.get_authenticated()

    def get_authenticated(self):

        url = self.base_url + '?username=' + self.username + ';password=' + self.password + ';agent=' + self.agent

        response = requests.get(url, headers=self.headers)

        # Check for errors in response
        try:
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            print('Error in get_authenticated: Connection Error')
            return None
        except requests.exceptions.HTTPError:
            print('Error in get_authenticated: HTTP Error ' + str(response.status_code))
            return None

        # QRZ offered valid response. Setup XML
        response_xml = ET.fromstring(response.content)
        xml_tree = ET.ElementTree(response_xml)
        root = xml_tree.getroot()

        # Check to see if authenticated.
        if 'Error' in root[0][0].tag:
            print('Error in get_authenticated: ' + root[0][0].text)
            return None
        else:
            try:
                self.version = root.attrib['version']
                self.session_key = root[0][0].text
                self.count = root[0][2].text
                self.expiration = root[0][3].text

                print('qrz_async: Authenticated!')
            except IndexError:
                print('Error in get_authenticated: IndexError likely due to incorrect url. ' + url)
                return None

    def _xml_to_dictionary(self, xml) -> dict:

        station = {}

        for child in xml.iter('*'):

            # Remove namespace
            tag = child.tag.split("}", 1)[1]

            # Ignore irrelevant elements, including details on the session
            if tag not in ['QRZDatabase', 'Callsign', 'Session', 'Key', 'Count', 'SubExp', 'GMTime', 'Remark', 'cpu']:
                # Create a dictionary of the station information
                station[tag] = child.text

        return station

    def get_details(self, query):

        self.stations = []

        # Check to see if session key is available
        if not self.session_key:
            self.get_authenticated()

        if isinstance(query, str):

            url = self.base_url + '?s=' + self.session_key + ';callsign=' + query

            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            status = response.status_code

            if status == 200:
                response_xml = ET.fromstring(response.content)

                station = self._xml_to_dictionary(response_xml)

                return station

        elif isinstance(query, list):

            urls = []

            for callsign in query:
                url = self.base_url + '?s=' + self.session_key + ';callsign=' + callsign

                urls.append(url)

            # Asyncio Run
            run(self._make_requests(urls=urls))

            # Results added to self.stations via self.call

        else:
            print('QRZ Error in get_qrz_details. Returning original input without details.')
            return self.stations

        return self.stations

    async def _call(self, url, session):

        try:
            response = await session.request(method='GET', url=url, headers=self.headers, timeout=self.timeout)
        except requests.exceptions.RequestException as error:
            print(error.strerror)
            return None

        result = await response.text()

        if response.status == 200:
            response_xml = ET.fromstring(result)

            station = self._xml_to_dictionary(response_xml)

            self.stations.append(station)

    async def _make_requests(self, urls):
        async with ClientSession(headers=self.headers, connector=TCPConnector(ssl=False)) as session:
            queue = []

            # Append the queue with calls
            for url in urls:
                queue.append(self._call(url=url, session=session))

            # Await for asyncio to run
            await gather(*queue)


if __name__ == "__main__":
    qrz = QRZ()
