r"""
nomnom is a command line tool to browse zomato straight from your terminal

Usage:
nomnom surprise
nomnom configure
nomnom search <restaurant-name>
nomnom test <restaurant-id> <dish>
nomnom menu <restaurant-id>
nomnom reviews <restaurant-id>
nomnom (-h | --help)
nomnom
Options:
  -h --help     Show this screen.
  --version     Show version.

"""

from docopt import docopt
import requests
import random
import json
from tabulate import tabulate
import sys

__version__ = "0.0.2"
headers = {}

try:
    config = json.loads(open("./config.json", "r").read())
    headers = {'Accept' : 'application/json', 'user_key': config['api_key'], 'User-Agent': 'curl/7.35.0'}
except:
    print("Failed to find configuration file, run configure()")
    print(sys.exc_info()[1])

def configure():
    configure_file = open("config.json", "w")
    api_key = input("Enter API key: ") or "9822cee7e33b3418662df7f5703b9624"
    budget = input("Enter budget: ") or "100"
    lat = input("Enter your latitude: ") or "18.44"
    lon = input("Enter your longitude: ") or "73.89"
    headers = {'Accept' : 'application/json', 'user_key': api_key, 'User-Agent': 'curl/7.35.0'}
    url = "https://developers.zomato.com/api/v2.1/cities?lat={0}&lon={1}".format(lat, lon)
    city_id = ""
    try:
        response = requests.get(url, headers = headers)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                city_id = data['location_suggestions'][0]['id']
        else:
            print("Error requesting, response code:"  + str(response.status_code))
    except:
        print("Error requesting")
        print(sys.exc_info()[1])

    if city_id:
        configuration_settings = {"api_key": api_key, "budget": budget, "latitude": lat, "longitude": lon}
        configure_file.write(json.dumps(configuration_settings))
    else:
        print("Could not retrieve city id for specified coordinates")

def surprise():
    url = 'https://developers.zomato.com/api/v2.1/geocode?lat={0}&lon={1}'.format(config['latitude'],config['longitude'])
    try:
        response = requests.get(url, headers = headers)
        if response.status_code == 200:
            data = response.json()
            restaurants = data['nearby_restaurants']
            res_len = len(restaurants)
            i = 0
            table = []
            while(i < res_len):
                cur_restaurant = restaurants[i]['restaurant']
                table.append([ cur_restaurant['id'] , cur_restaurant["name"], cur_restaurant["currency"] + " " + str(float(cur_restaurant['average_cost_for_two'])/2), cur_restaurant["user_rating"]["aggregate_rating"], cur_restaurant["location"]["address"][:50] ])
                i = i + 1
            print(tabulate(table, headers=["ID", "Name", "Budget", "Rating", "Location"]))
        else:
            print("Error requesting, response code:"  + str(response.status_code))
    except:
        print("Error requesting")
        print(sys.exc_info()[1])

def menu(restaurant_id):
    import re
    import os
    from urllib.parse import urlsplit
    url = 'https://developers.zomato.com/api/v2.1/restaurant?res_id={0}'.format(restaurant_id)
    print(url)
    headers = {'Accept' : 'application/json', 'user_key': config['api_key'], 'User-Agent': 'curl/7.35.0'}
    response = requests.get(url, headers = headers)
    if response.status_code == 200:
        data = response.json()
        print(data['menu_url'])
        menu_response = requests.get(data['menu_url'], headers = {'User-Agent': 'Mozilla/5.0 (iPad; U; CPU OS 3_2_1 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Mobile/7B405'})
        html_source = menu_response.text
        '''
        To print a string it must first be converted from pure Unicode to the
        byte sequences supported by your output device. This requires an encode
        to the proper character set, which Python has identified as cp850 - the
        Windows Console default.
        Starting with Python 3.4 you can set the Windows console to use UTF-8
        with the following command issued at the command prompt:

        chcp 65001
        '''
        x = re.search('zomato\.menuPage(.+}]);', html_source)
        matched_text = x.group(0)
        matched_text = matched_text[matched_text.find("["): -1]
        print(matched_text)
        menu_items = json.loads(matched_text)
        i = 0
        if not os.path.exists("image_cache/" + str(restaurant_id) + "/"):
            os.makedirs("image_cache/" + str(restaurant_id) + "/")
        while(i < len(menu_items)):
            cur_menu_url = menu_items[i]['url']
            print(cur_menu_url)
            suffix_list = ['jpg', 'png']
            file_name = "image_cache/" + str(restaurant_id) + "/" + urlsplit(cur_menu_url)[2].split('/')[-1]
            file_suffix = file_name.split('.')[1]
            menu_image_file = requests.get(cur_menu_url)
            if file_suffix in suffix_list and menu_image_file.status_code == requests.codes.ok:
                with open(file_name, 'wb') as file:
                    file.write(menu_image_file.content)
            i += 1
    else:
        print("Error requesting, response code:"  + str(response.status_code))

import queue as queue
q = queue.Queue()

def check_for_dish(image_file, restaurant_id, dish):
    from PIL import Image, ImageEnhance, ImageFilter
    import pytesseract
    from fuzzywuzzy import fuzz

    print(image_file)
    menu_image = Image.open('./image_cache/' + str(restaurant_id) + '/' + image_file)
    #menu_image.filter(ImageFilter.SHARPEN)
    menu_image = menu_image.convert('L', dither = 0)
    #menu_image.show()
    text = pytesseract.image_to_string(menu_image)
    text = text.split('\n')
    print("Finished computing OCR")
    for cur_line in text:
        if(cur_line != ' '):
            compare_ratio = fuzz.partial_ratio(dish, cur_line)
            if compare_ratio >= 80:
                print(cur_line)
                q.put(dish + " is available!")

def test(restaurant_id, dish):
    from os import listdir
    from os.path import isfile, join

    import threading
    image_path = "./image_cache/" + str(restaurant_id) + "/"
    image_list = [f for f in listdir(image_path) if isfile(join(image_path, f))]
    for image_file in image_list:
        print("lol")
        t = threading.Thread(target = check_for_dish, args = (image_file, restaurant_id, dish))
        t.daemon = True
        t.start()

    s = q.get()
    print(s)

def search(restaurant_name):
    url = 'https://developers.zomato.com/api/v2.1/search?q={0}&count=10&lat={1}&lon={2}'.format(restaurant_name, config['latitude'],config['longitude'])
    try:
        response = requests.get(url, headers = headers)
        if response.status_code == requests.codes.ok:
            data = response.json()
            restaurants = data['restaurants']
            res_len = len(restaurants)
            i = 0
            table = []
            while(i < res_len):
                cur_restaurant = restaurants[i]['restaurant']
                table.append([ cur_restaurant['id'] , cur_restaurant["name"], cur_restaurant["currency"] + " " + str(float(cur_restaurant['average_cost_for_two'])/2), cur_restaurant["user_rating"]["aggregate_rating"], cur_restaurant["location"]["address"][:50] ])
                i = i + 1
            print(tabulate(table, headers=["ID", "Name", "Budget", "Rating", "Location"]))
        else:
             print("Error requesting, response code:"  + str(response.status_code))
    except:
        print('Error requesting')
        print(sys.exc_info()[1])

def reviews(restaurant_id):
    url = 'https://developers.zomato.com/api/v2.1/reviews?res_id={0}&count=5'.format(restaurant_id)
    print(url)
    try:
        response = requests.get(url, headers = headers)
        if response.status_code == requests.codes.ok:
            data = response.json()
            reviews = data['user_reviews']
            rev_len = len(reviews)
            i = 0
            table = []
            while(i < rev_len):
                cur_review = reviews[i]['review']
                print("Time: " + cur_review['review_time_friendly'])
                print("Review: " + cur_review['review_text'])
                print("Rating: " + str(cur_review['rating']))
                print('\n')
                i = i + 1
        else:
             print("Error requesting, response code:"  + str(response.status_code))
    except:
        print('Error requesting')
        print(sys.exc_info()[1])
        
def main():
    arguments = docopt(__doc__, version = __version__)
    if arguments['configure']:
        configure()
    elif arguments['search']:
        search(arguments['<restaurant-name>'])
    elif arguments['surprise']:
        surprise()
    elif arguments['menu']:
        menu(arguments['<restaurant-id>'])
    elif arguments['reviews']:
        reviews(arguments['<restaurant-id>'])
    elif arguments['test']:
        test(arguments['<restaurant-id>'], arguments['<dish>'])
    else:
        print(__doc__)

if __name__ == '__main__':
    main()
