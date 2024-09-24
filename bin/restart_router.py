import requests
from requests.auth import HTTPDigestAuth
import os

from variables import *

def restart_fritzbox(url, username, password):
    location = "/upnp/control/deviceconfig"
    uri = "urn:dslforum-org:service:DeviceConfig:1"
    action = 'Reboot'
    url = f"{url}:49000{location}"
    headers = {
        'Content-Type': 'text/xml; charset="utf-8"',
        'SoapAction': f"{uri}#{action}"
    }
    body = f"""<?xml version='1.0' encoding='utf-8'?>
               <s:Envelope s:encodingStyle='http://schemas.xmlsoap.org/soap/encoding/' xmlns:s='http://schemas.xmlsoap.org/soap/envelope/'>
                   <s:Body>
                       <u:{action} xmlns:u='{uri}'></u:{action}>
                   </s:Body>
               </s:Envelope>"""

    try:
        response = requests.post(url, headers=headers, data=body, auth=HTTPDigestAuth(username, password), verify=False)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

restart_fritzbox(BASEURL, ROUTER_USER, ROUTER_PASSWORD)