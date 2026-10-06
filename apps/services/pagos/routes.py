"""
pagos/routes.py
Rutas del microservicio de Pagos (puerto 5005).
Procesa pagos simulados con verificación de idempotencia en Redis (evita doble cobro),
actualización atómica a status='confirmed' y consulta de comprobantes.
"""
import sys, os
_curr = os.path.abspath(__file__)
for _ in range(4):
    _curr = os.path.dirname(_curr)
    _cand = os.path.join(_curr, 'apps', 'services')
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)
    if os.path.isdir(os.path.join(_curr, 'common')) and _curr not in sys.path:
        sys.path.insert(0, _curr)

from decimal import Decimal
from flask import Blueprint, request, g
import psycopg.rows

from common import (
    get_connection,
    make_response_format,
    jwt_required,
    roles_required,
    redis_client,
    config
)

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')


# -----------------------------------------------------------------
# POST /payments -- REGISTRAR PAGO SIMULADO (CON IDEMPOTENCIA REDIS)
# -----------------------------------------------------------------
@payments_bp.route('', methods=['POST'])
@jwt_required()
def process_payment():
    """
    Registra un pago simulado para un pedido.
    Aplica IDEMPOTENCIA en Redis con clave 'payment:<order_id>' para evitar doble cobro.
    Actualiza el estado del pedido a 'confirmed' y almacena registro en simulated_payments.
    """
    user_id = g.jwt_user.get('user_id')
    role = (g.jwt_user.get('role') or '').lower()

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    order_id = data.get('order_id')
    amount_in = data.get('amount')
    raw_method = (data.get('method') or 'simulated_card').strip()
    method = 'simulated_card' if raw_method in ('tarjeta_simulada', 'tarjeta', 'card', 'simulated_card', '') else raw_method

    if not order_id:
        return make_response_format({'status': 'error', 'message': 'El campo order_id es obligatorio.'}, 400, request)

    try:
        order_id = int(order_id)
    except ValueError:
        return make_response_format({'status': 'error', 'message': 'order_id debe ser un entero.'}, 400, request)

    # 1. Comprobar Idempotencia previa en Redis
    idempotency_key = f"payment:order:{order_id}"
    cached_result = redis_client.get_idempotency_result(idempotency_key)
    if cached_result:
        cached_result['idempotent_replay'] = True
        return make_response_format(cached_result, 200, request)

    # 2. Adquirir lock / control de idempotencia atómico (Fail-Closed si Redis falla)
    acquired = redis_client.acquire_idempotency_key(idempotency_key, ttl_seconds=config.IDEMPOTENCY_TTL_SECONDS)
    if not acquired:
        return make_response_format({
            'status': 'error',
            'message': f'El pago para el pedido {order_id} ya se encuentra en procesamiento.'
        }, 409, request)

    # 3. Validar estado del pedido en PostgreSQL
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    "SELECT id, user_id, status, total FROM orders WHERE id = %s FOR UPDATE",
                    (order_id,)
                )
                order = cur.fetchone()

                if not order:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Pedido con ID {order_id} no encontrado.'
                    }, 404, request)

                # Validar propiedad
                if role != 'admin' and order['user_id'] != user_id:
                    return make_response_format({
                        'status': 'error',
                        'message': 'No autorizado para pagar este pedido.'
                    }, 403, request)

                # Validar que esté en 'pending'
                current_status = order['status'].lower()
                if current_status != 'pending':
                    return make_response_format({
                        'status': 'error',
                        'message': f"El pedido no puede pagarse porque se encuentra en estado '{current_status}'."
                    }, 400, request)

                # Validar monto coincidente (requerido por trg_validate_simulated_payment)
                expected_total = Decimal(str(order['total']))
                payment_amount = Decimal(str(amount_in)) if amount_in is not None else expected_total

                if payment_amount != expected_total:
                    return make_response_format({
                        'status': 'error',
                        'message': f'El monto del pago (${payment_amount}) no coincide con el total del pedido (${expected_total}).'
                    }, 400, request)

                # 4. Insertar pago simulado
                cur.execute(
                    """INSERT INTO simulated_payments (order_id, method, status, amount, processed_at)
                       VALUES (%s, %s, 'approved', %s, now())
                       RETURNING id, processed_at""",
                    (order_id, method, payment_amount)
                )
                payment_row = cur.fetchone()
                payment_id = payment_row['id']
                processed_at = payment_row['processed_at']

                # 5. Actualizar pedido a 'confirmed'
                cur.execute(
                    "UPDATE orders SET status = 'confirmed', updated_at = now() WHERE id = %s",
                    (order_id,)
                )
                conn.commit()

        # 6. Almacenar resultado de idempotencia en Redis
        result_payload = {
            'status': 'success',
            'message': 'Pago procesado y pedido confirmado exitosamente.',
            'payment': {
                'id': payment_id,
                'order_id': order_id,
                'amount': float(payment_amount),
                'method': method,
                'status': 'approved',
                'processed_at': processed_at
            },
            'order': {
                'id': order_id,
                'status': 'confirmed'
            }
        }
        redis_client.set_idempotency_result(idempotency_key, result_payload, ttl_seconds=config.IDEMPOTENCY_TTL_SECONDS)
        redis_client.delete_cache(f"order:pending:{order_id}")

        return make_response_format(result_payload, 201, request)

    except Exception as e:
        # Liberar la clave de idempotencia si falló la transacción
        redis_client.delete_cache(f"idempotency:{idempotency_key}")
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# GET /payments/order/<order_id> -- CONSULTAR PAGOS DE UN PEDIDO
# -----------------------------------------------------------------
@payments_bp.route('/order/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_payments(order_id):
    """Consulta los comprobantes de pago registrados para un pedido."""
    user_id = g.jwt_user.get('user_id')
    role = (g.jwt_user.get('role') or '').lower()

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                # Verificar pedido
                cur.execute("SELECT id, user_id, status, total FROM orders WHERE id = %s", (order_id,))
                order = cur.fetchone()
                if not order:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Pedido {order_id} no encontrado.'
                    }, 404, request)

                if role != 'admin' and order['user_id'] != user_id:
                    return make_response_format({
                        'status': 'error',
                        'message': 'No autorizado para consultar los pagos de este pedido.'
                    }, 403, request)

                cur.execute(
                    """SELECT id, order_id, method, status, amount, processed_at
                         FROM simulated_payments
                        WHERE order_id = %s
                        ORDER BY id DESC""",
                    (order_id,)
                )
                payments = cur.fetchall()

        return make_response_format({
            'status': 'success',
            'order_id': order_id,
            'payments': payments,
            'count': len(payments)
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)
