"""
helpers/response.py
Función central para responder en XML o JSON según el parámetro ?format=.
XML es el formato predeterminado.
"""
from flask import jsonify, Response, request as flask_request
from dicttoxml import dicttoxml


def make_response_format(data, status_code, request=None):
    """
    Genera una respuesta HTTP en XML o JSON.

    Args:
        data: dict con los datos de la respuesta.
        status_code: código HTTP (200, 201, 400, etc.).
        request: objeto request de Flask (si es None, usa el request actual).

    Returns:
        Tupla (Response, status_code) lista para retornar desde un endpoint.
    """
    req = request or flask_request
    fmt = req.args.get('format', 'xml').lower()

    if fmt == 'json':
        response = jsonify(data)
        response.status_code = status_code
        return response
    else:
        xml_bytes = dicttoxml(data, custom_root='response', attr_type=False)
        return Response(
            xml_bytes,
            status=status_code,
            mimetype='application/xml'
        )

