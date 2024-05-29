import base64
import requests

from .utils import print_error, bcolor


class BasicAuthToken(requests.auth.AuthBase):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __call__(self, r):
        authstr = 'Basic ' + base64.b64encode(bytes(self.key + ":" + self.value, 'utf-8')).decode('utf-8')
        r.headers['Authorization'] = authstr
        return r


class KomootApi:
    def __init__(self):
        self.user_id = ''
        self.token = ''

    def __build_header(self):
        if self.user_id and self.token:
            return BasicAuthToken(self.user_id, self.token)
        return None

    @staticmethod
    def __send_request(url, auth, critical=True):
        r = requests.get(url, auth=auth)
        if r.status_code != 200:
            print_error("Error " + str(r.status_code) + ": " + str(r.json()))
            if critical:
                exit(1)
        return r

    def login(self, email, password):
        print("Logging in...")

        r = self.__send_request("https://api.komoot.de/v006/account/email/" + email + "/",
                                BasicAuthToken(email, password))

        self.user_id = r.json()['username']
        self.token = r.json()['password']

        print("Logged in as '" + r.json()['user']['displayname'] + "'")

    def fetch_tours(self, tourType="all", silent=False):
        if not silent:
            print("Fetching tours of user '" + self.user_id + "'...")

        results = {}
        has_next_page = True
        current_uri = "https://api.komoot.de/v007/users/" + self.user_id + "/tours/"
        while has_next_page:
            r = self.__send_request(current_uri, self.__build_header())

            has_next_page = 'next' in r.json()['_links'] and 'href' in r.json()['_links']['next']
            if has_next_page:
                current_uri = r.json()['_links']['next']['href']

            tours = r.json()['_embedded']['tours']
            for tour in tours:
                if tourType != "all" and tourType != tour['type']:
                    continue
                results[tour['id']] = tour;

        print("Found " + str(len(results)) + " tours")
        return results

    def print_tours(self, tourType="all"):
        tours = self.fetch_tours(tourType, silent=True)
        print()
        for tour_id, tour in tours.items():
            descr =  tour['name'] + " (" + tour['sport'] + "; " + str(int(tour['distance']) / 1000.0) + "km; " + tour['type'] + ")"
            print(bcolor.BOLD + bcolor.HEADER + str(tour_id) + bcolor.ENDC + " => " + bcolor.BOLD + descr + bcolor.ENDC)

        if len(tours) < 1:
            print_error("No tours found on your profile")

    def fetch_tour(self, tour_id):
        print("Fetching tour '" + tour_id + "'...")

        r = self.__send_request("https://api.komoot.de/v007/tours/" + tour_id + "?_embedded=coordinates,way_types,"
                                                                                "surfaces,directions,participants,"
                                                                                "timeline&directions=v2&fields"
                                                                                "=timeline&format=coordinate_array"
                                                                                "&timeline_highlights_fields=tips,"
                                                                                "recommenders",
                                self.__build_header())

        return r.json()

    def fetch_highlight_tips(self, highlight_id):
        print("Fetching highlight '" + highlight_id + "'...")

        r = self.__send_request("https://api.komoot.de/v007/highlights/" + highlight_id + "/tips/",
                                self.__build_header(), critical=False)

        return r.json()
