"""
helpers/response.py
Formateador dual XML / JSON para el microservicio de libros.
XML por defecto, JSON con ?format=json.
"""
import decimal
import datetime
from flask import jsonify, Response, request as flask_request
from dicttoxml import dicttoxml


def _serialize_types(obj):
    """Convierte recursivamente Decimals a float y datetimes a ISO string."""
    if isinstance(obj, dict):
        return {k: _serialize_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_types(v) for v in obj]
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return obj


def make_response_format(data, status_code, request=None):
    """Genera respuesta HTTP en XML o JSON según ?format=."""
    req = request or flask_request
    fmt = req.args.get('format', 'xml').lower()

    clean_data = _serialize_types(data)

    if fmt == 'json':
        resp = jsonify(clean_data)
        resp.status_code = status_code
        return resp
    else:
        xml_bytes = dicttoxml(clean_data, custom_root='response', attr_type=False)
        return Response(xml_bytes, status=status_code, mimetype='application/xml')
