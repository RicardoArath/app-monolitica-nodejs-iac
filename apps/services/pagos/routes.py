"""
pagos/routes.py
Rutas del microservicio de Pagos (puerto 5002).
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
    valid_methods = ('simulated_card', 'tarjeta_simulada', 'tarjeta', 'card', '',
                     'tarjeta_credito', 'tarjeta_debito', 'transferencia', 'paypal_simulado')
    method = 'simulated_card' if raw_method in valid_methods else raw_method
    notes = (data.get('notes') or '').strip() or None

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
                    redis_client.release_idempotency_key(idempotency_key)
                    return make_response_format({
                        'status': 'error',
                        'message': f'Pedido con ID {order_id} no encontrado.'
                    }, 404, request)

                # Validar propiedad
                if role != 'admin' and order['user_id'] != user_id:
                    redis_client.release_idempotency_key(idempotency_key)
                    return make_response_format({
                        'status': 'error',
                        'message': 'No autorizado para pagar este pedido.'
                    }, 403, request)

                current_status = order['status'].lower()

                # Si el pedido ya está pagado/confirmado, responder idempotentemente con el comprobante existente
                if current_status in ('confirmed', 'completed', 'shipped'):
                    cur.execute(
                        """SELECT id, order_id, method, status, amount, notes, processed_at
                             FROM simulated_payments WHERE order_id = %s""",
                        (order_id,)
                    )
                    existing_payment = cur.fetchone()
                    if existing_payment:
                        result_payload = {
                            'status': 'success',
                            'message': f'El pedido #{order_id} ya fue pagado exitosamente con anterioridad.',
                            'payment': dict(existing_payment),
                            'order': {
                                'id': order_id,
                                'status': current_status
                            },
                            'idempotent_replay': True
                        }
                        redis_client.set_idempotency_result(idempotency_key, result_payload, ttl_seconds=config.IDEMPOTENCY_TTL_SECONDS)
                        return make_response_format(result_payload, 200, request)

                # Validar que esté en 'pending'
                if current_status != 'pending':
                    redis_client.release_idempotency_key(idempotency_key)
                    return make_response_format({
                        'status': 'error',
                        'message': f"El pedido #{order_id} no puede pagarse porque se encuentra en estado '{current_status.upper()}'."
                    }, 400, request)

                # Validar monto coincidente (requerido por trg_validate_simulated_payment)
                expected_total = Decimal(str(order['total']))
                payment_amount = Decimal(str(amount_in)) if amount_in is not None else expected_total

                if payment_amount != expected_total:
                    redis_client.release_idempotency_key(idempotency_key)
                    return make_response_format({
                        'status': 'error',
                        'message': f'El monto del pago (${payment_amount}) no coincide con el total del pedido (${expected_total}).'
                    }, 400, request)

                # 4. Insertar pago simulado
                cur.execute(
                    """INSERT INTO simulated_payments (order_id, method, status, amount, notes, processed_at)
                       VALUES (%s, %s, 'approved', %s, %s, now())
                       RETURNING id, processed_at""",
                    (order_id, method, payment_amount, notes)
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
                'notes': notes,
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
        redis_client.release_idempotency_key(idempotency_key)
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# GET /payments -- LISTAR PAGOS (SOPORTA ?order_id=, ?page=, ?limit=, FORMATO DUAL)
# -----------------------------------------------------------------
@payments_bp.route('', methods=['GET'])
@jwt_required()
def list_payments():
    """
    Lista pagos registrados con soporte de filtro por order_id y paginación.
    Responde en formato dual JSON/XML según cabeceras o parámetro format.
    """
    user_id = g.jwt_user.get('user_id')
    role = (g.jwt_user.get('role') or '').lower()

    order_id_arg = request.args.get('order_id', '').strip()
    page_arg = request.args.get('page', '1').strip()
    limit_arg = request.args.get('limit', '20').strip()

    try:
        page = max(1, int(page_arg))
    except ValueError:
        page = 1

    try:
        limit = max(1, min(100, int(limit_arg)))
    except ValueError:
        limit = 20

    offset = (page - 1) * limit

    conditions = []
    params = []

    # Seguridad: Usuarios regulares solo ven pagos de sus propias órdenes
    if role != 'admin':
        conditions.append("o.user_id = %s")
        params.append(user_id)

    if order_id_arg:
        try:
            oid = int(order_id_arg)
            conditions.append("sp.order_id = %s")
            params.append(oid)
        except ValueError:
            return make_response_format({'status': 'error', 'message': 'order_id debe ser un entero.'}, 400, request)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                # Contar total para paginación
                cur.execute(
                    f"""SELECT COUNT(*) AS total
                          FROM simulated_payments sp
                          JOIN orders o ON o.id = sp.order_id
                        {where_clause}""",
                    params
                )
                total_count = cur.fetchone()['total']

                # Obtener pagos
                query = f"""SELECT sp.id, sp.order_id, sp.method, sp.status, sp.amount,
                                   sp.notes, sp.processed_at, o.user_id
                              FROM simulated_payments sp
                              JOIN orders o ON o.id = sp.order_id
                            {where_clause}
                            ORDER BY sp.id DESC
                            LIMIT %s OFFSET %s"""
                cur.execute(query, params + [limit, offset])
                payments = cur.fetchall()

        return make_response_format({
            'status': 'success',
            'payments': payments,
            'count': len(payments),
            'total': total_count,
            'page': page,
            'limit': limit
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# GET /payments/<id> -- DETALLE DE PAGO POR ID
# -----------------------------------------------------------------
@payments_bp.route('/<int:payment_id>', methods=['GET'])
@jwt_required()
def get_payment(payment_id):
    """Consulta los datos de un comprobante de pago por su ID único."""
    user_id = g.jwt_user.get('user_id')
    role = (g.jwt_user.get('role') or '').lower()

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    """SELECT sp.id, sp.order_id, sp.method, sp.status, sp.amount,
                              sp.notes, sp.processed_at, o.user_id, o.status AS order_status
                         FROM simulated_payments sp
                         JOIN orders o ON o.id = sp.order_id
                        WHERE sp.id = %s""",
                    (payment_id,)
                )
                payment = cur.fetchone()

        if not payment:
            return make_response_format({
                'status': 'error',
                'message': f'Pago con ID {payment_id} no encontrado.'
            }, 404, request)

        if role != 'admin' and payment['user_id'] != user_id:
            return make_response_format({
                'status': 'error',
                'message': 'No autorizado para consultar este pago.'
            }, 403, request)

        return make_response_format({
            'status': 'success',
            'payment': payment
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# PATCH /payments/<id> -- ACTUALIZAR ESTADO O NOTAS DEL PAGO
# -----------------------------------------------------------------
@payments_bp.route('/<int:payment_id>', methods=['PATCH'])
@jwt_required()
def update_payment(payment_id):
    """
    Actualiza el estado o notas de un comprobante de pago.
    Si se cambia el estado a 'refunded' o 'cancelled', sincroniza la orden a 'cancelled'.
    """
    user_id = g.jwt_user.get('user_id')
    role = (g.jwt_user.get('role') or '').lower()

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    new_status = data.get('status')
    notes = data.get('notes')

    if new_status is None and notes is None:
        return make_response_format({
            'status': 'error',
            'message': 'Debe enviar al menos un campo para actualizar: status o notes.'
        }, 400, request)

    if new_status is not None:
        new_status = str(new_status).strip().lower()
        valid_statuses = ['approved', 'rejected', 'refunded', 'cancelled']
        if new_status not in valid_statuses:
            return make_response_format({
                'status': 'error',
                'message': f"Estado inválido '{new_status}'. Opciones: {', '.join(valid_statuses)}"
            }, 400, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    """SELECT sp.id, sp.order_id, sp.status, sp.amount, sp.notes, o.user_id, o.status AS order_status
                         FROM simulated_payments sp
                         JOIN orders o ON o.id = sp.order_id
                        WHERE sp.id = %s FOR UPDATE""",
                    (payment_id,)
                )
                payment = cur.fetchone()

                if not payment:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Pago con ID {payment_id} no encontrado.'
                    }, 404, request)

                # Control de permisos: solo admin o dueño del pedido
                if role != 'admin':
                    if payment['user_id'] != user_id:
                        return make_response_format({
                            'status': 'error',
                            'message': 'No autorizado para modificar este pago.'
                        }, 403, request)
                    # Usuario regular no puede auto-aprobar pagos
                    if new_status and new_status not in ('cancelled', 'refunded'):
                        return make_response_format({
                            'status': 'error',
                            'message': 'Solo un administrador puede asignar ese estado.'
                        }, 403, request)

                order_id = payment['order_id']
                prev_status = payment['status']
                set_clauses = []
                params = []

                if new_status is not None:
                    set_clauses.append("status = %s")
                    params.append(new_status)
                if notes is not None:
                    set_clauses.append("notes = %s")
                    params.append(str(notes).strip())

                if set_clauses:
                    params.append(payment_id)
                    cur.execute(
                        f"UPDATE simulated_payments SET {', '.join(set_clauses)} WHERE id = %s",
                        params
                    )

                # Si cambia a refunded o cancelled, sincronizar orden y restaurar stock si estaba confirmada
                if new_status in ('refunded', 'cancelled') and prev_status == 'approved':
                    cur.execute(
                        "UPDATE orders SET status = 'cancelled', updated_at = now() WHERE id = %s",
                        (order_id,)
                    )
                    cur.execute(
                        "SELECT book_id, quantity FROM order_items WHERE order_id = %s",
                        (order_id,)
                    )
                    items = cur.fetchall()
                    for item in items:
                        cur.execute(
                            "UPDATE books SET stock = stock + %s WHERE id = %s",
                            (item['quantity'], item['book_id'])
                        )

                conn.commit()

        # Invalidaciones de caché en Redis
        if new_status in ('refunded', 'cancelled'):
            redis_client.delete_cache(f"payment:order:{order_id}")
            redis_client.delete_cache(f"idempotency:payment:order:{order_id}")
            redis_client.invalidate_pattern('books:*')

        return make_response_format({
            'status': 'success',
            'message': f'Pago {payment_id} actualizado exitosamente.',
            'payment_id': payment_id,
            'order_id': order_id,
            'previous_status': prev_status,
            'status': new_status if new_status is not None else prev_status,
            'notes': notes if notes is not None else payment['notes']
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# DELETE /payments/<id> -- ANULAR/REVERSAR PAGO
# -----------------------------------------------------------------
@payments_bp.route('/<int:payment_id>', methods=['DELETE'])
@jwt_required()
def delete_payment(payment_id):
    """
    Anula/reversa un pago: actualiza su estado a 'refunded',
    sincroniza el estado de la orden a 'cancelled',
    restaura atómicamente el stock en PostgreSQL e invalida caché en Redis.
    """
    user_id = g.jwt_user.get('user_id')
    role = (g.jwt_user.get('role') or '').lower()

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    """SELECT sp.id, sp.order_id, sp.status, sp.amount, o.user_id, o.status AS order_status
                         FROM simulated_payments sp
                         JOIN orders o ON o.id = sp.order_id
                        WHERE sp.id = %s FOR UPDATE""",
                    (payment_id,)
                )
                payment = cur.fetchone()

                if not payment:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Pago con ID {payment_id} no encontrado.'
                    }, 404, request)

                if role != 'admin' and payment['user_id'] != user_id:
                    return make_response_format({
                        'status': 'error',
                        'message': 'No autorizado para anular este pago.'
                    }, 403, request)

                order_id = payment['order_id']
                prev_status = payment['status']

                if prev_status in ('refunded', 'cancelled'):
                    return make_response_format({
                        'status': 'error',
                        'message': f'El pago ya se encuentra en estado {prev_status}.'
                    }, 400, request)

                # 1. Actualizar estado del pago a 'refunded'
                cur.execute(
                    """UPDATE simulated_payments
                          SET status = 'refunded',
                              notes = COALESCE(notes, '') || ' [Anulado/Reversado]'
                        WHERE id = %s""",
                    (payment_id,)
                )

                # 2. Sincronizar estado de la orden a 'cancelled'
                cur.execute(
                    "UPDATE orders SET status = 'cancelled', updated_at = now() WHERE id = %s",
                    (order_id,)
                )

                # 3. Restaurar stock atómicamente si el pago estaba aprobado previamente
                if prev_status == 'approved':
                    cur.execute(
                        "SELECT book_id, quantity FROM order_items WHERE order_id = %s",
                        (order_id,)
                    )
                    items = cur.fetchall()
                    for item in items:
                        cur.execute(
                            "UPDATE books SET stock = stock + %s WHERE id = %s",
                            (item['quantity'], item['book_id'])
                        )

                conn.commit()

        # 4. Invalidaciones en Redis
        redis_client.delete_cache(f"payment:order:{order_id}")
        redis_client.delete_cache(f"idempotency:payment:order:{order_id}")
        redis_client.invalidate_pattern('books:*')

        return make_response_format({
            'status': 'success',
            'message': f'Pago {payment_id} anulado/reversado exitosamente y orden sincronizada a cancelada.',
            'payment_id': payment_id,
            'order_id': order_id,
            'previous_status': prev_status,
            'new_status': 'refunded'
        }, 200, request)
    except Exception as e:
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
                    """SELECT id, order_id, method, status, amount, notes, processed_at
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
