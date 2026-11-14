from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import io
import json
import threading
import unittest
from unittest.mock import patch

import cloud_server


class StubRouting:
    def __init__(self): self.calls=[]
    def health(self): return {'status':'ready','depth_checked':False}
    def route(self,start,finish):
        self.calls.append((start,finish))
        return 200,{'status':'ok','points':[{'lon':p[0],'lat':p[1]}for p in(start,finish)]}


@contextmanager
def server(routing):
    with patch.object(cloud_server,'MARINE_ROUTES',routing):
        httpd=ThreadingHTTPServer(('127.0.0.1',0),cloud_server.Handler)
        thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
        try:yield httpd.server_port
        finally:httpd.shutdown();httpd.server_close();thread.join(3)


def request(port,path):
    connection=HTTPConnection('127.0.0.1',port,timeout=5)
    try:
        connection.request('GET',path);response=connection.getresponse()
        return response.status,dict(response.getheaders()),response.read()
    finally:connection.close()


class RoutingHTTPTests(unittest.TestCase):
    def test_http_uses_lon_lat_and_preserves_cors_and_no_store(self):
        routing=StubRouting()
        with server(routing)as port:
            status,headers,body=request(port,'/route?start_lat=17.1&start_lon=-61.9&end_lat=16.3&end_lon=-61.8')
        self.assertEqual(status,200)
        self.assertEqual(routing.calls,[((-61.9,17.1),(-61.8,16.3))])
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertEqual(headers['Access-Control-Allow-Origin'],'*')
        self.assertEqual(json.loads(body)['status'],'ok')

    def test_bad_queries_never_reach_the_planner(self):
        routing=StubRouting()
        with server(routing)as port:
            for query in ['','start_lat=x','start_lat=17&start_lat=18&start_lon=-62&end_lat=17&end_lon=-61',
                          'start_lat=17&start_lon=-62&end_lat=17&end_lon=-61&extra=1']:
                self.assertEqual(request(port,'/route?'+query)[0],400)
        self.assertEqual(routing.calls,[])

    def test_existing_health_and_radar_work_without_routing_data(self):
        class Unavailable(StubRouting):
            def health(self):return {'status':'loading'}
        with server(Unavailable())as port:
            self.assertEqual(request(port,'/routing/health')[0],503)
            self.assertEqual(request(port,'/health')[0],200)
            status,headers,_=request(port,'/radar?lat=17.1&lon=-61.8&name=Antigua')
            self.assertEqual(status,302)
            self.assertTrue(headers['Location'].startswith('https://ajecv27.github.io/seapoint-backend/'))

    def test_route_queries_are_not_written_to_access_log(self):
        output=io.StringIO()
        with patch('sys.stderr',output),server(StubRouting())as port:
            request(port,'/route?start_lat=17.123456&start_lon=-61.987654&end_lat=17&end_lon=-61.8')
        self.assertNotIn('17.123456',output.getvalue())
        self.assertNotIn('61.987654',output.getvalue())


if __name__=='__main__':unittest.main()
