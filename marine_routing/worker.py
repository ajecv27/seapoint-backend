"""One isolated routing worker; no HTTP listener or private-coordinate logging."""
import json
import os
import resource
import sys


def send(data):
    print(json.dumps(data, separators=(',', ':'), allow_nan=False), flush=True)


def main():
    os.environ['SEAPOINT_ROUTE_TIMING'] = '0'
    try:
        from . import engine
        manifest = engine.initialize()
        send({'type': 'ready', 'dataset': manifest['id'],
              'build': engine.ROUTING_BUILD, 'coastline_policy': engine.COASTLINE_POLICY,
              'rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    except Exception as error:
        print('Routing initialization failed: ' + type(error).__name__, file=sys.stderr, flush=True)
        send({'type': 'unavailable'})
        return
    for line in sys.stdin:
        if len(line) > 2048:
            return
        try:
            token = None
            request = json.loads(line)
            token = request['id']
            result = engine.route(tuple(request['start']), tuple(request['finish']), seconds=18)
            send({'id': token, 'status': 200, 'body': result,
                  'rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
        except engine.RouteTimeout:
            send({'id': token, 'status': 504, 'body': {'status': 'error',
                  'error': 'Route calculation took too long. Try a shorter route or move the endpoints into open water.'}})
        except ValueError as error:
            send({'id': token, 'status': 400, 'body': {'status': 'error', 'error': str(error)}})
        except Exception as error:
            print('Routing request failed: ' + type(error).__name__, file=sys.stderr, flush=True)
            send({'id': token, 'status': 503, 'body': {'status': 'error',
                  'error': 'Routing is temporarily unavailable. Please try again.'}})


if __name__ == '__main__':
    main()
