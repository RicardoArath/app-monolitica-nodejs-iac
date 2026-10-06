"""
common/response.py
Generación centralizada de respuestas duales (JSON y XML) para todos los microservicios.
Soporta:
  - ?format=json (o cabecera Accept: application/json)
  - ?format=xml  (o cabecera Accept: application/xml)
Convierte automáticamente tipos no serializables como Decimal, datetime y UUID.
"""
from datetime import date, datetime
from decimal import Decimal
import json
from uuid import UUID

import dicttoxml
from flask import Response, jsonify, request as flask_request

# Desactivar logs ruidosos de dicttoxml
dicttoxml.LOG.setLevel(50)


def _sanitize_data(data):
    """Convierte tipos complejos (Decimal, datetime, UUID) a primitivos serializables."""
    if isinstance(data, dict):
        return {k: _sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple, set)):
        return [_sanitize_data(item) for item in data]
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    elif isinstance(data, UUID):
        return str(data)
    return data


def make_response_format(data, status_code=200, req=None):
    """
    Construye una respuesta HTTP en JSON o XML según el parámetro 'format' o headers.
    Por defecto retorna JSON.
    """
    r = req or flask_request

    # Determinar formato solicitado
    req_format = 'json'
    if r is not None:
        fmt_arg = r.args.get('format', '').lower().strip()
        accept = r.headers.get('Accept', '').lower()
        if fmt_arg == 'xml' or ('application/xml' in accept and fmt_arg != 'json'):
            req_format = 'xml'
        elif fmt_arg == 'json' or 'application/json' in accept:
            req_format = 'json'

    sanitized = _sanitize_data(data)

    if req_format == 'xml':
        try:
            xml_bytes = dicttoxml.dicttoxml(
                sanitized,
                custom_root='response',
                attr_type=False
            )
            return Response(
                xml_bytes,
                status=status_code,
                mimetype='application/xml; charset=utf-8'
            )
        except Exception:
            # Fallback a JSON en caso de error en serialización XML
            req_format = 'json'

    # Formato JSON por defecto
    json_str = json.dumps(sanitized, ensure_ascii=False)
    return Response(
        json_str,
        status=status_code,
        mimetype='application/json; charset=utf-8'
    )
