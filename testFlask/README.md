This is a Flask + Spyne working together example. It is very simple, absolutely sinthetic and does nothing useful. Again, it's just an example.

Create virtualenv and install requirements

pip install Flask
pip install -e . # install Spyne from working directory
Run Flask web server

./examples/flask/manage.py
Try Flask views to make sure it works

curl -s http://127.0.0.1:5000/hello | python -m json.tool
Here is a Spyne views call example

curl -s http://localhost:5000/soap/hello?name=Anton\&times=3 | python -m json.tool