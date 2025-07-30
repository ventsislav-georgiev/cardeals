import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from utils import db as cardb

class CarDBHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/cars.json':
            cardb.init_db()
            rows = cardb.get_all_cars()
            cars = []
            for row in rows:
                # row is a dict: id, link, data, status, last_seen, removed_date, created_date
                try:
                    car_dict = json.loads(row.get('data', '')) if row.get('data') else {}
                except Exception:
                    car_dict = {}
                car_dict.setdefault('id', row.get('id'))
                car_dict.setdefault('listing_url', row.get('link'))
                car_dict['status'] = row.get('status', '')
                car_dict['last_seen'] = row.get('last_seen', '')
                car_dict['removed_date'] = row.get('removed_date', '')
                car_dict['created_date'] = row.get('created_date', '')
                for key in ['brand', 'model', 'year', 'price', 'currency', 'kilometers', 'location', 'image_urls']:
                    car_dict.setdefault(key, '')
                if not isinstance(car_dict.get('image_urls'), list):
                    car_dict['image_urls'] = []
                cars.append(car_dict)
            results = {
                'search_params': {},
                'search_url': None,
                'total_results': len(cars),
                'timestamp': '',
                'cars': cars
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(results, ensure_ascii=False, indent=2).encode('utf-8'))
        else:
            try:
                with open('docs/index.html', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(content)
            except Exception:
                self.send_error(404, 'File not found')

def run(server_class=HTTPServer, handler_class=CarDBHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Serving on http://localhost:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
