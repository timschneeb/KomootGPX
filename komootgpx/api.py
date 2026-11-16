import sys
import base64
import json
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
    def __init__(self, debug=False):
        self.user_id = ''
        self.token = ''
        self.request_count = 0
        self.debug = debug
        self.share_token = None

    def __build_header(self):
        if self.user_id and self.token:
            return BasicAuthToken(self.user_id, self.token)
        return None

    def __send_request(self, url, auth, critical=True):
        self.request_count += 1
        r = requests.get(url, auth=auth)

        if self.debug:
            with open(f"komootgpx-debug-{self.request_count}.txt", "w", encoding="utf-8") as dbgf:
                dbgf.write(r.text)

        if r.status_code != 200:
            print_error("Error " + str(r.status_code) + ": " + str(r.json()))
            if critical:
                sys.exit(1)
        return r

    def login(self, email, password):
        print("Logging in...")

        r = self.__send_request("https://api.komoot.de/v006/account/email/" + email + "/",
                                    BasicAuthToken(email, password))

        rj = r.json()
        self.user_id = rj['username']
        self.token = rj['password']
        self.display_name = rj["user"]["displayname"]

        print("Logged in as '" + self.display_name + "'")

    def login_with_token(self, user_id, token, display_name):
        print("Logging in with token...")

        self.user_id = user_id
        self.token = token
        self.display_name = display_name

        print("Logged in as '" + self.display_name + "'")

    def fetch_tours(self, tour_type="tour_all", silent=False):
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
                if tour_type != "tour_all" and tour_type != tour['type']:
                    continue
                results[tour['id']] = tour

        print("Found " + str(len(results)) + " tours")
        return results

    def fetch_tour(self, tour_id, language="en"):
        print("Fetching tour '" + tour_id + "'...")

        r = self.__send_request("https://api.komoot.de/v007/tours/" + tour_id + "?_embedded=coordinates,way_types,"
                                                                                "surfaces,directions,participants,"
                                                                                "timeline&hl=" + language + "&directions=v2&fields"
                                                                                "=timeline&format=coordinate_array"
                                                                                "&timeline_highlights_fields=tips,"
                                                                                "recommenders"
                                                                                + ("&share_token=" + self.share_token if self.share_token else ""),
                                self.__build_header())
        return r.json()

    def fetch_highlight_tips(self, highlight_id):
        print("Fetching highlight '" + highlight_id + "'...")

        r = self.__send_request("https://api.komoot.de/v007/highlights/" + highlight_id + "/tips/",
                                self.__build_header(), critical=False)

        return r.json()

    def fetch_tour_images(self, tour_id, silent=False):
        if not silent:
            print("Fetching images of tour '" + str(tour_id) + "'...")

        results = {}
        has_next_page = True
        current_uri = "https://api.komoot.de/v007/tours/" + tour_id + "/cover_images/"
        while has_next_page:
            r = self.__send_request(current_uri, self.__build_header())

            has_next_page = 'next' in r.json()['_links'] and 'href' in r.json()['_links']['next']
            if has_next_page:
                current_uri = r.json()['_links']['next']['href']

            images = r.json().get('_embedded', {}).get('items', [])
            for image in images:
                results[image['id']] = image

        print("Found " + str(len(results)) + " images")
        return results

    def fetch_highlight(self, highlight_id, silent=False):
        if not silent:
            print("Fetching highlight '" + str(highlight_id) + "'...")

        results = {}
        current_uri = "https://api.komoot.de/v007/highlights/" + str(highlight_id)
        r = self.__send_request(current_uri, self.__build_header())

        return r.json()
