"""
common/metrics.py
Métricas en memoria por proceso, expuestas en GET /metrics con formato de
texto de Prometheus. No requiere dependencias externas.

Métricas principales:
  http_requests_total{method,endpoint,status}
  http_request_duration_seconds_sum / _count
  redis_cache_hits_total{prefix} / redis_cache_misses_total{prefix}
  redis_cache_bypass_total{prefix}       (Redis caído -> lectura directa a PostgreSQL)
  redis_cache_invalidations_total{pattern}
  redis_errors_total{operation}
  jwt_rejected_total{reason}
  jwt_issued_total / jwt_revoked_total
"""
import threading
import time

_lock = threading.Lock()
_counters = {}
_summaries = {}
START_TIME = time.time()

_HELP = {
    'http_requests_total': 'Total de peticiones HTTP atendidas.',
    'http_request_duration_seconds': 'Duración de las peticiones HTTP.',
    'redis_cache_hits_total': 'Lecturas servidas desde la caché de Redis.',
    'redis_cache_misses_total': 'Lecturas no encontradas en caché (consulta a PostgreSQL).',
    'redis_cache_bypass_total': 'Lecturas que omitieron la caché porque Redis no estaba disponible.',
    'redis_cache_invalidations_total': 'Claves de caché invalidadas tras escrituras.',
    'redis_errors_total': 'Errores de comunicación con Redis.',
    'jwt_rejected_total': 'JWT rechazados por motivo.',
    'jwt_issued_total': 'JWT de acceso emitidos.',
    'jwt_revoked_total': 'JWT revocados (lista jwt:revoked:<jti>).',
}


def _key(name, labels):
    return name, tuple(sorted((k, str(v)) for k, v in labels.items()))


def inc(name, value=1, **labels):
    with _lock:
        k = _key(name, labels)
        _counters[k] = _counters.get(k, 0) + value


def observe(name, value, **labels):
    with _lock:
        k = _key(name, labels)
        s = _summaries.setdefault(k, [0.0, 0])
        s[0] += value
        s[1] += 1


def snapshot():
    with _lock:
        return dict(_counters), {k: list(v) for k, v in _summaries.items()}


def _fmt_labels(labels):
    if not labels:
        return ''
    inner = ','.join(f'{k}="{v}"' for k, v in labels)
    return '{' + inner + '}'


def render(service_name):
    counters, summaries = snapshot()
    lines = [
        '# HELP service_uptime_seconds Segundos desde el arranque del servicio.',
        '# TYPE service_uptime_seconds gauge',
        f'service_uptime_seconds{{service="{service_name}"}} {round(time.time() - START_TIME, 2)}',
    ]
    seen = set()
    for (name, labels), value in sorted(counters.items()):
        if name not in seen:
            lines.append(f'# HELP {name} {_HELP.get(name, name)}')
            lines.append(f'# TYPE {name} counter')
            seen.add(name)
        lines.append(f'{name}{_fmt_labels(labels)} {value}')
    for (name, labels), (total, count) in sorted(summaries.items()):
        if name not in seen:
            lines.append(f'# HELP {name} {_HELP.get(name, name)}')
            lines.append(f'# TYPE {name} summary')
            seen.add(name)
        lines.append(f'{name}_sum{_fmt_labels(labels)} {round(total, 6)}')
        lines.append(f'{name}_count{_fmt_labels(labels)} {count}')
    return '\n'.join(lines) + '\n'
