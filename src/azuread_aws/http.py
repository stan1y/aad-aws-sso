'''
HTTP/HTTPS requests wrapper using standard library.

Available response properties
* resp.data             Raw response data in bytes
* resp.text             Response data encoded into text, None if not a string
* resp.json             Response data as a dictionary if response is JSON, None otherwise
* resp.ok               True if status_code [200,400)
* resp.status           Alias for status_code
* resp.status_code      HTTP status code
* resp.reason           HTTP status reason
* resp.headers          Dictionary of HTTP headers
'''
import http
import urllib.parse
import json
import logging
import base64


log = logging.getLogger('http')


def get(url, auth=None, headers=None, params=None):
    return call(url, method='GET', auth=auth, headers=headers, params=params)


def head(url, auth=None, headers=None, params=None):
    return call(url, method='HEAD', auth=auth, headers=headers, params=params)


def delete(url, auth=None, headers=None, params=None):
    return call(url, method='DELETE', auth=auth, headers=headers, params=params)


def put(url, data, auth=None, headers=None, params=None):
    return call(url, method='PUT', auth=auth, headers=headers, data=data, params=params)


def patch(url, data, auth=None, headers=None, params=None):
    return call(url, method='PATCH', auth=auth, headers=headers, data=data, params=params)


def post(url, data, auth=None, headers=None, params=None):
    return call(url, method='POST', auth=auth, headers=headers, data=data, params=params)


def encode_data(data, headers):
    content_type = headers.get('Content-Type', '')
    if isinstance(data, (dict, list)):
        if isinstance(data, dict) and 'application/x-www-form-urlencoded' in content_type:
            # send body with urlencoded data
            encoded = urllib.parse.urlencode(data)
        else:
            # send body as serialzied json string
            headers['Content-Type'] = 'application/json'
            encoded = json.dumps(data)

    elif isinstance(data, str):
        encoded = data
    else:
        raise Exception(f'Unsupported data type {type(data)} for http calls')

    if 'Content-Type' not in headers:
        headers['Content-Type'] = 'text/plain'

    headers['Content-Length'] = len(encoded)
    return encoded


def call(url, method='GET', auth=None, headers=None, data=None, params=None, redirect_limit=3):
    ''' Wrapper for HTTP(s) API calls
        * The URL to make a call to
        * method - HTTP method to use: GET, HEAD, POST, PUT, DELETE, OPTIONS
        * auth - Value to base64 encode for the Authorization header
        * headers - Dictionary with user defined headers
        * data - Payload for POST and put methods. Dictionaries and lists are automatically converted to JSON
    '''

    log.debug('%s %s', method, url)
    hdrs = headers.copy() if headers and isinstance(headers, dict) else {}

    # set auth info if given
    if auth:
        encoded = base64.b64encode(bytes(auth, 'utf-8')).decode('utf-8')
        hdrs['Authorization'] = f'Basic {encoded}'

    # serialize data and set length
    if data:
        data = encode_data(data, hdrs)

    url_o = urllib.parse.urlparse(url)

    if url_o.scheme == 'https':
        con = http.client.HTTPSConnection(url_o.netloc)
    elif url_o.scheme == 'http':
        con = http.client.HTTPConnection(url_o.netloc)
    else:
        raise Exception('unsupported scheme (' + url_o.scheme + ')')

    query = '?' + url_o.query if url_o.query else ''

    if params:
        if query:
            query = '&'.join([query, urllib.parse.urlencode(params)])
        else:
            query = '?' + urllib.parse.urlencode(params)

    headers = '; '.join(['%s: %s' % (h, hdrs[h]) for h in hdrs])
    log.debug('%s headers: %s %s%s', method, headers, url_o.path, query)
    if data:
        log.debug('<- %s', data)

    con.request(method, url_o.path + query, body=data, headers=hdrs)
    resp = con.getresponse()

    resp.data = resp.read()
    resp.json = None
    resp.text = None

    con.close()

    log.debug('%s response %s -> %d %s', method, url, resp.status, resp.reason)

    resp.status_code = resp.status
    resp.ok = 200 <= resp.status < 400

    # redirect
    if resp.status_code in [301, 302, 307, 308]:
        if redirect_limit > 0:
            return call(resp.headers['Location'], method, auth, headers, data, params, redirect_limit - 1)

    try:
        resp.text = resp.data.decode('utf-8')
    except UnicodeDecodeError:
        pass

    if resp.headers.get('Content-Type') is not None \
            and 'application/json' in resp.headers.get('Content-Type'):
        try:
            resp.json = json.loads(resp.text)
        except json.JSONDecodeError:
            pass

    return resp
