import requests
import json
import pprint

url = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
r = requests.get(url, params={'size':10})
response_json = json.loads(r.text)
print(response_json['hits']['hits'][1]['_source'])