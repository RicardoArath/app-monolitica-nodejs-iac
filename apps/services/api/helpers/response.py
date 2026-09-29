"""
helpers/response.py
Funcion central para responder en XML o JSON segun el parametro ?format=.
XML es el formato predeterminado.
"""
from flask import jsonify, Response, request as flask_request
from dicttoxml import dicttoxml
import decimal
import datetime

def make_response_format(data, status_code, request=None):
    """
    Genera una respuesta HTTP en XML o JSON.
    """
    req = request or flask_request
    fmt = req.args.get('format', 'xml').lower()

    def convert_types(d):
        if isinstance(d, dict):
            return {k: convert_types(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [convert_types(v) for v in d]
        elif isinstance(d, decimal.Decimal):
            return float(d)
        elif isinstance(d, (datetime.datetime, datetime.date)):
            return d.isoformat()
        return d
    
    clean_data = convert_types(data)

    if fmt == 'json':
        response = jsonify(clean_data)
        response.status_code = status_code
        return response
    else:
        xml_bytes = dicttoxml(clean_data, custom_root='response', attr_type=False)
        return Response(
            xml_bytes,
            status=status_code,
            mimetype='application/xml'
        )
