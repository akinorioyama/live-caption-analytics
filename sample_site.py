"""
Sample online speaking session

Usage:
  sample_site.py <host> <port>
  sample_site.py -h | --help
  sample_site.py --version

  <host>:
  <port>:

Examples:
  sample_site.py 0.0.0.0 443

Options:
  -h --help     Show this screen.
  --version     Show version.
"""

from docopt import docopt

from flask import Flask, request, jsonify,json
from flask_cors import CORS
from flask import render_template

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
CORS(app)

@app.route('/lca/sample_speaking_session',methods=['POST','GET'])
def return_session_template_to_test():
    text = render_template('sample_speaking_session.html')
    return text

@app.route('/lca_status/sample_session_copy',methods=['POST','GET'])
def return_session_copy():
    text = render_template('show_session_copy.html')
    return text


if __name__ == "__main__":

    arguments = docopt(__doc__, version="0.1")

    host = arguments["<host>"]
    port = int(arguments["<port>"])
    app.run(debug=False, host=host, port=int(port), ssl_context=('cert/cert.pem', 'cert/key.pem'))