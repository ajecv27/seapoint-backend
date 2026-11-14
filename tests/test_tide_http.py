from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import io
import json
import tempfile
import threading
import unittest
from unittest.mock import patch

import cloud_server
from tide_service import TideService


@contextmanager
def server(service):
    with patch.object(cloud_server,'TIDE_SERVICE',service), patch.object(cloud_server,'WORLDTIDES_API_KEY','test-only'):
        httpd=ThreadingHTTPServer(('127.0.0.1',0),cloud_server.Handler)
        thread=threading.Thread(target=httpd.serve_forever,daemon=True)
        thread.start()
        try:yield httpd.server_port
        finally:httpd.shutdown();httpd.server_close();thread.join(3)


def request(port,path,token=None,method='GET'):
    connection=HTTPConnection('127.0.0.1',port,timeout=5)
    try:
        headers={'X-SeaPoint-Tide-Client':token}if token else{}
        connection.request(method,path,headers=headers)
        response=connection.getresponse()
        return response.status,dict(response.getheaders()),response.read()
    finally:connection.close()


class TideHTTPTests(unittest.TestCase):
    def test_legacy_requests_do_not_spend_credits_and_options_allow_client_header(self):
        with tempfile.TemporaryDirectory()as folder:
            calls=[]
            service=TideService(lambda *args:calls.append(args),directory=folder)
            with server(service)as port:
                status,headers,body=request(port,'/tides?lat=17.12&lon=-61.8')
                self.assertEqual(status,428)
                self.assertEqual(json.loads(body)['reason'],'client_update_required')
                self.assertEqual(headers['Cache-Control'],'no-store')
                status,headers,_=request(port,'/tides',method='OPTIONS')
                self.assertEqual(status,204)
                self.assertIn('X-SeaPoint-Tide-Client',headers['Access-Control-Allow-Headers'])
                self.assertEqual(request(port,'/health')[0],200)
            self.assertEqual(calls,[])

    def test_credit_error_is_stable_private_and_pauses_the_next_http_request(self):
        with tempfile.TemporaryDirectory()as folder:
            calls=[]
            def fetch(*args):calls.append(args);return {'status':402,'error':'Insufficient credits; secret should not escape'}
            service=TideService(fetch,directory=folder)
            output=io.StringIO()
            with patch('sys.stderr',output),server(service)as port:
                for token in ['a'*32,'b'*32]:
                    status,_,body=request(port,'/tides?lat=17.123456&lon=-61.8',token)
                    self.assertEqual(status,503)
                    self.assertEqual(json.loads(body)['reason'],'credits_exhausted')
                    self.assertNotIn('secret',body.decode())
                status,_,body=request(port,'/tides/status')
                self.assertEqual(status,200)
                self.assertEqual(json.loads(body)['status'],'paused')
            self.assertNotIn('17.123456',output.getvalue())
            self.assertEqual(len(calls),1)


if __name__=='__main__':unittest.main()
